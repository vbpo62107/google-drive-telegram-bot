import asyncio
import os
import threading
import time
from typing import Dict, Optional, Set

import aiofiles
import aiohttp
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import DOWNLOAD_DIRECTORY, LOGGER, MAX_CONCURRENT_MIRRORS, MAX_MIRROR_FILE_SIZE
from bot.helpers.sql_helper import get_session
from bot.helpers.sql_helper.mirror_tasks import MirrorTask, MirrorTaskStatus
from bot.helpers.utils import (
    format_bytes,
    format_elapsed_eta,
    format_speed,
    render_progress_bar,
)
from bot.modules.drive_helper import get_drive_instance


class TaskCancelled(Exception):
    pass


class TaskPaused(Exception):
    pass


class TaskRetry(Exception):
    pass


class MirrorTaskRunner:
    def __init__(self, manager: "TaskManager", record: MirrorTask):
        self.manager = manager
        self.id = record.id
        self.user_id = record.user_id
        self.chat_id = record.chat_id
        self.message_id = record.message_id
        self.url = record.url
        self.file_name = record.file_name
        self.stage = record.stage
        self.paused = record.paused or record.status == MirrorTaskStatus.PAUSED.value
        self._pause_requested = False
        self._cancel_requested = False
        self._last_error = record.error
        self._download_dir = os.path.join(DOWNLOAD_DIRECTORY, f"task_{self.id}")
        self._destination = os.path.join(self._download_dir, self.file_name)
        self._temp_path = self._destination + ".part"
        self._last_update = 0.0
        self._stage_start = time.monotonic()
        self._downloaded = record.processed_bytes
        self._total = record.total_bytes
        self._speed = record.speed
        self._drive_link: Optional[str] = record.drive_link
        self._lock = asyncio.Lock()
        self._upload_pause_event = threading.Event()
        self._upload_pause_event.set()

    async def refresh(self) -> MirrorTask:
        def op():
            with get_session() as session:
                return session.query(MirrorTask).get(self.id)

        return await asyncio.to_thread(op)

    async def set_message_id(self, message_id: int) -> MirrorTask:
        def op():
            with get_session() as session:
                record = session.query(MirrorTask).get(self.id)
                record.message_id = message_id
                record.updated_at = record.updated_at
                session.add(record)
                session.commit()
                session.refresh(record)
                return record

        record = await asyncio.to_thread(op)
        self.message_id = record.message_id
        return record

    async def request_pause(self) -> bool:
        async with self._lock:
            if self.paused:
                return False
            self._pause_requested = True
            self.paused = True
        await self._update_status(MirrorTaskStatus.PAUSED, "已暂停", paused=True)
        return True

    async def request_resume(self) -> bool:
        async with self._lock:
            if not self.paused:
                return False
            self._pause_requested = False
            self.paused = False
        await self._update_status(MirrorTaskStatus.PENDING, "等待恢复", paused=False, processed_bytes=0, total_bytes=0, speed=0)
        return True

    async def request_cancel(self) -> bool:
        async with self._lock:
            if self._cancel_requested:
                return False
            self._cancel_requested = True
            self.paused = False
            self._pause_requested = False
        self._upload_pause_event.set()
        await self._update_status(MirrorTaskStatus.CANCELLED, "已取消", paused=False)
        return True

    async def execute(self) -> str:
        if self._cancel_requested:
            return "cancelled"
        if self.paused:
            return "paused"
        try:
            await self._run()
            await self._update_status(MirrorTaskStatus.COMPLETED, "完成", paused=False, drive_link=self._drive_link)
            await self._final_message(success=True)
            return "completed"
        except TaskPaused:
            await self._update_status(MirrorTaskStatus.PAUSED, "已暂停", paused=True)
            await self._final_message(success=False)
            return "paused"
        except TaskCancelled:
            await self._update_status(MirrorTaskStatus.CANCELLED, "已取消", paused=False)
            await self._final_message(success=False)
            return "cancelled"
        except TaskRetry as exc:
            record = await self._mark_retry(str(exc))
            if record.retry_count <= record.max_retries:
                await self._notify_waiting_retry(record.retry_count, record.max_retries)
                return "retry"
            await self._update_status(MirrorTaskStatus.FAILED, "失败", paused=False, error=str(exc))
            await self._final_message(success=False)
            return "failed"
        except Exception as exc:
            await self._update_status(MirrorTaskStatus.FAILED, "失败", paused=False, error=str(exc))
            await self._final_message(success=False)
            return "failed"
        finally:
            await self._cleanup()

    async def _run(self) -> None:
        self._upload_pause_event.set()
        await self._update_status(MirrorTaskStatus.RUNNING, "准备中", paused=False, processed_bytes=0, total_bytes=0, speed=0, error=None)
        os.makedirs(self._download_dir, exist_ok=True)
        await self._download()
        await self._upload()

    async def _download(self) -> None:
        if self.url.startswith("tg://"):
            await self._download_from_telegram()
        else:
            await self._download_from_http()

    async def _download_from_http(self) -> None:
        attempt = 0
        while True:
            attempt += 1
            try:
                await self._perform_http_download()
                return
            except ValueError as exc:
                raise exc
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt >= 3:
                    raise TaskRetry(str(exc))
                await asyncio.sleep(min(4 * attempt, 16))

    async def _perform_http_download(self) -> None:
        self._stage_start = time.monotonic()
        self._downloaded = 0
        self._total = 0
        timeout = aiohttp.ClientTimeout(total=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.url) as response:
                if response.status >= 400:
                    raise ValueError(f"HTTP {response.status}")
                length = response.headers.get("Content-Length")
                self._total = int(length) if length else 0
                if self._total and self._total > MAX_MIRROR_FILE_SIZE:
                    raise ValueError("文件大小超出限制")
                await self._update_status(MirrorTaskStatus.RUNNING, "下载中", total_bytes=self._total, processed_bytes=0)
                async with aiofiles.open(self._temp_path, "wb") as file:
                    async for chunk in response.content.iter_chunked(1024 * 64):
                        await self._check_control()
                        if not chunk:
                            continue
                        projected = self._downloaded + len(chunk)
                        if projected > MAX_MIRROR_FILE_SIZE:
                            raise ValueError("文件大小超出限制")
                        await file.write(chunk)
                        self._downloaded = projected
                        await self._handle_progress("下载中", self._downloaded, self._total)
                if self._downloaded:
                    await self._handle_progress("下载中", self._downloaded, self._total, force=True)
        await asyncio.to_thread(os.replace, self._temp_path, self._destination)

    async def _download_from_telegram(self) -> None:
        if not self.manager.client:
            raise ValueError("客户端不可用")
        parts = self.url[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError("无效的 Telegram 源")
        try:
            chat_id = int(parts[0])
            message_id = int(parts[1])
        except ValueError as exc:
            raise ValueError("无效的 Telegram 源") from exc
        message = await self.manager.client.get_messages(chat_id, message_id)
        media = None
        for attr in ("document", "video", "audio", "voice", "photo", "animation"):
            media = getattr(message, attr, None)
            if media:
                break
        if not media:
            raise ValueError("未找到可下载的媒体")
        size = getattr(media, "file_size", 0) or 0
        if size and size > MAX_MIRROR_FILE_SIZE:
            raise ValueError("文件大小超出限制")
        self._stage_start = time.monotonic()
        self._downloaded = 0
        self._total = size
        await self._update_status(MirrorTaskStatus.RUNNING, "下载中", total_bytes=size, processed_bytes=0)

        async def progress(current: int, total: int) -> None:
            self._downloaded = current
            self._total = total
            await self._check_control()
            await self._handle_progress("下载中", current, total)

        await self.manager.client.download_media(
            message,
            file_name=self._temp_path,
            progress=progress,
        )
        if not os.path.exists(self._temp_path):
            raise ValueError("下载失败")
        if self._downloaded:
            await self._handle_progress("下载中", self._downloaded, self._total, force=True)
        await asyncio.to_thread(os.replace, self._temp_path, self._destination)

    async def _upload(self) -> None:
        drive = await get_drive_instance(self.user_id)
        upload_total = await asyncio.to_thread(self._determine_upload_size)
        self._stage_start = time.monotonic()
        await self._update_status(MirrorTaskStatus.RUNNING, "上传中", total_bytes=upload_total, processed_bytes=0)

        async def progress_callback(transferred, total):
            await self._check_control()
            await self._handle_progress("上传中", transferred, total)

        def cancelled():
            return self._cancel_requested or self._pause_requested

        try:
            result = await drive.upload_file_with_progress(
                self._destination,
                progress_callback=progress_callback,
                pause_event=self._upload_pause_event,
                cancel_callback=cancelled,
            )
        except RuntimeError as exc:
            if "cancelled" in str(exc):
                if self._cancel_requested:
                    raise TaskCancelled("已取消")
                raise TaskPaused("已暂停")
            raise
        if result.startswith("✅"):
            self._drive_link = result
            await self._handle_progress("上传中", upload_total, upload_total, force=True)
        elif result.startswith("❗") or result.startswith("**ERROR"):
            raise TaskRetry(result)
        else:
            raise TaskRetry(result)

    async def _handle_progress(self, stage_text: str, processed: int, total: int, force: bool = False) -> None:
        now = time.monotonic()
        elapsed = max(now - self._stage_start, 0.001)
        speed = processed / elapsed
        if not force and now - self._last_update < 1.5 and processed < total:
            await self._update_cached_progress(processed, total, speed, stage_text)
            return
        self._last_update = now
        await self._update_status(MirrorTaskStatus.RUNNING, stage_text, processed_bytes=processed, total_bytes=total, speed=speed)
        await self._update_message(stage_text, processed, total, speed)

    async def _update_cached_progress(self, processed: int, total: int, speed: float, stage_text: str) -> None:
        await self._update_status(None, stage_text, processed_bytes=processed, total_bytes=total, speed=speed)

    async def _update_status(self, status: Optional[MirrorTaskStatus], stage_text: str, **fields) -> MirrorTask:
        def op():
            with get_session() as session:
                record = session.query(MirrorTask).get(self.id)
                if status is not None:
                    record.status = status.value
                record.stage = stage_text
                for key, value in fields.items():
                    setattr(record, key, value)
                session.add(record)
                session.commit()
                session.refresh(record)
                return record

        record = await asyncio.to_thread(op)
        self.stage = record.stage
        self._downloaded = record.processed_bytes
        self._total = record.total_bytes
        self._speed = record.speed
        self._last_error = record.error
        self._drive_link = record.drive_link
        self.paused = record.paused
        if record.message_id and status is not None:
            if status in {MirrorTaskStatus.CANCELLED, MirrorTaskStatus.FAILED, MirrorTaskStatus.COMPLETED}:
                await self._update_message(stage_text, record.processed_bytes, record.total_bytes, record.speed, final=True)
            elif status == MirrorTaskStatus.PAUSED:
                await self._update_message(stage_text, record.processed_bytes, record.total_bytes, record.speed)
        return record

    async def _update_message(self, stage_text: str, processed: int, total: int, speed: float, final: bool = False) -> None:
        if not self.manager.client or not self.message_id:
            return
        bar = render_progress_bar(processed, total)
        percent = (processed / total * 100) if total else 0
        total_text = format_bytes(total) if total else "未知大小"
        speed_text = format_speed(speed)
        elapsed_text, eta_text = format_elapsed_eta(time.monotonic() - self._stage_start, processed, total)
        lines = [
            f"📄 `{self.file_name}`",
            f"🔗 {self.url}",
            f"📊 {stage_text}",
            f"{bar} {percent:.2f}%",
            f"☁️ {format_bytes(processed)} / {total_text}",
            f"⚡ {speed_text}",
            f"⏱️ {elapsed_text}",
            f"⏳ {eta_text}",
        ]
        if self._drive_link and stage_text == "完成":
            lines.append(self._drive_link)
        keyboard = self._build_keyboard(final)
        try:
            await self.manager.client.edit_message_text(
                self.chat_id,
                self.message_id,
                "\n".join(lines),
                reply_markup=keyboard,
            )
        except Exception as exc:
            LOGGER.warning("Failed to update message for task %s: %s", self.id, exc)

    def _build_keyboard(self, final: bool) -> Optional[InlineKeyboardMarkup]:
        if final:
            return None
        pause_button = InlineKeyboardButton("⏸️ 暂停", callback_data=f"mirror:{self.id}:pause")
        resume_button = InlineKeyboardButton("▶️ 继续", callback_data=f"mirror:{self.id}:resume")
        cancel_button = InlineKeyboardButton("🛑 取消", callback_data=f"mirror:{self.id}:cancel")
        if self.paused or self._pause_requested:
            buttons = [[resume_button, cancel_button]]
        else:
            buttons = [[pause_button, cancel_button]]
        return InlineKeyboardMarkup(buttons)

    async def _final_message(self, success: bool) -> None:
        if not self.manager.client or not self.message_id:
            return
        record = await self.refresh()
        status = record.status
        if status == MirrorTaskStatus.COMPLETED.value and self._drive_link:
            text = self._drive_link
            markup = None
        elif status == MirrorTaskStatus.PAUSED.value:
            return
        elif status == MirrorTaskStatus.CANCELLED.value:
            text = f"🛑 任务已取消\nID: {self.id}"
            markup = None
        elif status == MirrorTaskStatus.FAILED.value:
            text = f"❌ 任务失败\n{record.error or ''}"
            markup = None
        else:
            text = f"ℹ️ 任务状态: {status}"
            markup = None
        try:
            await self.manager.client.edit_message_text(self.chat_id, self.message_id, text, reply_markup=markup)
        except Exception as exc:
            LOGGER.warning("Failed to send final message for task %s: %s", self.id, exc)

    async def _notify_waiting_retry(self, retry_count: int, max_retries: int) -> None:
        if not self.manager.client or not self.message_id:
            return
        text = f"🔁 重试 {retry_count}/{max_retries}\nID: {self.id}"
        keyboard = self._build_keyboard(False)
        try:
            await self.manager.client.edit_message_text(self.chat_id, self.message_id, text, reply_markup=keyboard)
        except Exception as exc:
            LOGGER.warning("Failed to notify retry for task %s: %s", self.id, exc)

    async def _mark_retry(self, error: str) -> MirrorTask:
        def op():
            with get_session() as session:
                record = session.query(MirrorTask).get(self.id)
                record.retry_count += 1
                record.error = error
                record.status = MirrorTaskStatus.PENDING.value
                record.stage = "等待重试"
                record.processed_bytes = 0
                record.total_bytes = 0
                record.speed = 0
                record.paused = False
                record.drive_link = None
                session.add(record)
                session.commit()
                session.refresh(record)
                return record

        record = await asyncio.to_thread(op)
        self.paused = False
        self._pause_requested = False
        self._cancel_requested = False
        self._drive_link = None
        return record

    async def _cleanup(self) -> None:
        for path in (self._temp_path, self._destination):
            if os.path.exists(path):
                try:
                    await asyncio.to_thread(os.remove, path)
                except FileNotFoundError:
                    pass
        if os.path.isdir(self._download_dir):
            try:
                await asyncio.to_thread(os.rmdir, self._download_dir)
            except OSError:
                pass

    async def _check_control(self) -> None:
        if self._cancel_requested:
            raise TaskCancelled("已取消")
        if self._pause_requested:
            raise TaskPaused("已暂停")

    def _determine_upload_size(self) -> int:
        return os.path.getsize(self._destination)


class TaskManager:
    def __init__(self, concurrency_limit: int):
        self.concurrency_limit = concurrency_limit
        self.client = None
        self._queue: asyncio.Queue[MirrorTaskRunner] = asyncio.Queue()
        self._runners: Dict[int, MirrorTaskRunner] = {}
        self._pending: Set[int] = set()
        self._workers = []
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self, client) -> None:
        async with self._init_lock:
            if self._initialized:
                if self.client is None:
                    self.client = client
                return
            self.client = client
            for _ in range(self.concurrency_limit):
                self._workers.append(asyncio.create_task(self._worker_loop()))
            await self._recover_tasks()
            self._initialized = True

    async def submit(self, client, user_id: int, chat_id: int, url: str, file_name: str) -> MirrorTaskRunner:
        await self.initialize(client)

        def op():
            with get_session() as session:
                record = MirrorTask(
                    user_id=user_id,
                    chat_id=chat_id,
                    url=url,
                    file_name=file_name,
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record

        record = await asyncio.to_thread(op)
        runner = MirrorTaskRunner(self, record)
        self._runners[runner.id] = runner
        if runner.message_id is not None:
            await self._queue.put(runner)
        else:
            self._pending.add(runner.id)
        return runner

    async def update_message_id(self, task_id: int, message_id: int) -> None:
        runner = self._runners.get(task_id)
        if runner:
            await runner.set_message_id(message_id)
            if task_id in self._pending:
                self._pending.discard(task_id)
                await self._queue.put(runner)

    async def pause(self, client, task_id: int) -> bool:
        await self.initialize(client)
        runner = self._runners.get(task_id)
        if not runner:
            record = await self._load_task(task_id)
            if not record:
                return False
            runner = MirrorTaskRunner(self, record)
            self._runners[task_id] = runner
        changed = await runner.request_pause()
        return changed

    async def resume(self, client, task_id: int) -> bool:
        await self.initialize(client)
        runner = self._runners.get(task_id)
        if not runner:
            record = await self._load_task(task_id)
            if not record:
                return False
            runner = MirrorTaskRunner(self, record)
            self._runners[task_id] = runner
        changed = await runner.request_resume()
        if changed:
            await self._queue.put(runner)
        return changed

    async def cancel(self, client, task_id: int) -> bool:
        await self.initialize(client)
        runner = self._runners.get(task_id)
        if not runner:
            record = await self._load_task(task_id)
            if not record:
                return False
            runner = MirrorTaskRunner(self, record)
            self._runners[task_id] = runner
        changed = await runner.request_cancel()
        if changed:
            self._pending.discard(task_id)
        return changed

    async def _worker_loop(self) -> None:
        while True:
            runner = await self._queue.get()
            try:
                await self._semaphore.acquire()
                try:
                    result = await runner.execute()
                finally:
                    self._semaphore.release()
                if result == "retry":
                    await asyncio.sleep(5)
                    await self._queue.put(runner)
                elif result == "paused":
                    pass
                elif result in {"completed", "cancelled", "failed"}:
                    self._runners.pop(runner.id, None)
                    self._pending.discard(runner.id)
            except Exception as exc:
                LOGGER.error("Worker error for task %s: %s", runner.id, exc)
            finally:
                self._queue.task_done()

    async def _recover_tasks(self) -> None:
        records = await asyncio.to_thread(self._fetch_incomplete_records)
        for record in records:
            runner = MirrorTaskRunner(self, record)
            self._runners[runner.id] = runner
            if record.status in {MirrorTaskStatus.PENDING.value, MirrorTaskStatus.RUNNING.value} and not record.paused:
                await self._queue.put(runner)

    def _fetch_incomplete_records(self):
        with get_session() as session:
            query = session.query(MirrorTask).filter(MirrorTask.status.in_([
                MirrorTaskStatus.PENDING.value,
                MirrorTaskStatus.RUNNING.value,
                MirrorTaskStatus.PAUSED.value,
            ]))
            return list(query.all())

    async def _load_task(self, task_id: int) -> Optional[MirrorTask]:
        def op():
            with get_session() as session:
                return session.query(MirrorTask).get(task_id)

        return await asyncio.to_thread(op)


task_manager = TaskManager(MAX_CONCURRENT_MIRRORS)
