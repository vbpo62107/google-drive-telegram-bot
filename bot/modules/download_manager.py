import asyncio
import cgi
import contextlib
import ipaddress
import json
import mimetypes
import os
import re
import secrets
import socket
import tempfile
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse, urljoin

import aiofiles
import httpx
import yt_dlp
from pyrogram import Client, filters
from pyrogram.errors import AuthBytesInvalid, FloodWait, RPCError
from pyrogram.file_id import FileId

from bot import DOWNLOAD_DIRECTORY, MAX_MIRROR_FILE_SIZE, SUDO_USERS, LOGGER
from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters, humanbytes, get_floodwait_seconds
from bot.modules.drive_helper import DriveAccessError, drive_error_message
from bot.modules.gdriveTools import GoogleDriveHelper

ALLOWED_CONTENT_PREFIXES = ("application/", "audio/", "video/", "image/", "text/plain")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
YT_DLP_CONCURRENCY = 2
YT_DLP_RATE_LIMIT = None
DOWNLOAD_PATH = Path(DOWNLOAD_DIRECTORY)
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)


class FetchError(RuntimeError):
    pass


@dataclass
class FetchResult:
    path: str
    name: str
    mime_type: Optional[str]
    size: int


class Fetcher(ABC):
    @abstractmethod
    async def fetch(self, client: Client, message, **kwargs) -> FetchResult:
        raise NotImplementedError


def sanitize_filename(name: str) -> str:
    if not name:
        return "file"
    cleaned = re.sub(r"[\n\r\t]", " ", name)
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = re.sub(r"[\x00-\x1F]+", "", cleaned)
    cleaned = cleaned.strip(" .")
    return cleaned or "file"


def unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base = sanitize_filename(filename)
    stem, ext = os.path.splitext(base)
    counter = 0
    while True:
        candidate = directory / (base if counter == 0 else f"{stem}_{counter}{ext}")
        if not candidate.exists():
            return candidate
        counter += 1


class DirectLinkFetcher(Fetcher):
    def __init__(self, directory: Path, max_size: int) -> None:
        self.directory = directory
        self.max_size = max_size
        self.limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)
        self.timeout = httpx.Timeout(30.0, connect=10.0, read=60.0)
        self.max_redirects = 5

    async def fetch(self, client: Client, message, **kwargs) -> FetchResult:
        url = kwargs.get("url")
        preferred = kwargs.get("preferred_name")
        if not url:
            raise FetchError("缺少下载链接")
        resolver_cache: dict[str, set[str]] = {}
        await self._assert_safe_destination(url, resolver_cache)
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout, follow_redirects=False) as session:
            head = await self._head(session, url, headers, resolver_cache)
            mime_type = None
            size_hint = None
            filename = None
            if head is not None:
                try:
                    mime_type = self._normalize_type(head.headers.get("Content-Type"))
                    size_hint = self._parse_length(head.headers.get("Content-Length"))
                    filename = self._extract_filename(head.headers.get("Content-Disposition"))
                    if size_hint and size_hint > self.max_size:
                        raise FetchError("文件大小超出限制")
                    if mime_type and not self._is_allowed_type(mime_type):
                        raise FetchError("文件类型不在白名单内")
                finally:
                    head.close()
            try:
                response, final_url = await self._follow_redirects(
                    session, "GET", url, headers, resolver_cache, stream=True
                )
                try:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise FetchError(str(exc)) from exc
                    if mime_type is None:
                        mime_type = self._normalize_type(response.headers.get("Content-Type"))
                        if mime_type and not self._is_allowed_type(mime_type):
                            raise FetchError("文件类型不在白名单内")
                    actual_length = self._parse_length(response.headers.get("Content-Length"))
                    if actual_length and actual_length > self.max_size:
                        raise FetchError("文件大小超出限制")
                    if preferred:
                        filename = sanitize_filename(preferred)
                    if not filename:
                        filename = self._extract_filename(response.headers.get("Content-Disposition"))
                    if not filename:
                        candidate = Path(unquote(urlparse(final_url).path or "")).name
                        filename = sanitize_filename(candidate or self._guess_filename(mime_type))
                    else:
                        filename = sanitize_filename(filename)
                    final_path = unique_path(self.directory, filename)
                    temp_path = final_path.with_suffix(final_path.suffix + ".part")
                    downloaded = 0
                    try:
                        async with aiofiles.open(temp_path, "wb") as handle:
                            async for chunk in response.aiter_bytes(65536):
                                if not chunk:
                                    continue
                                downloaded += len(chunk)
                                if downloaded > self.max_size:
                                    raise FetchError("文件大小超出限制")
                                await handle.write(chunk)
                        await asyncio.to_thread(os.replace, temp_path, final_path)
                        return FetchResult(str(final_path), final_path.name, mime_type, downloaded)
                    except Exception:
                        with contextlib.suppress(FileNotFoundError):
                            os.remove(temp_path)
                        raise
                finally:
                    await response.aclose()
            except httpx.RequestError as exc:
                raise FetchError(str(exc))
        raise FetchError("下载失败")

    async def _head(
        self,
        session: httpx.AsyncClient,
        url: str,
        headers: dict,
        cache: dict[str, set[str]],
    ) -> Optional[httpx.Response]:
        try:
            response, _ = await self._follow_redirects(
                session, "HEAD", url, headers, cache, stream=False
            )
        except FetchError:
            raise
        except httpx.RequestError:
            return None
        if response.is_error:
            response.close()
            return None
        return response

    async def _resolve(self, hostname: str) -> set[str]:
        loop = asyncio.get_running_loop()
        def op():
            try:
                return {info[4][0] for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)}
            except socket.gaierror:
                return set()
        return await loop.run_in_executor(None, op)

    def _is_forbidden_ip(self, ip: str) -> bool:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return True
        if str(address) == "169.254.169.254":
            return True
        return any([
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
        ])

    def _parse_length(self, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def _assert_safe_destination(
        self, url: str, cache: dict[str, set[str]]
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise FetchError("仅支持 HTTP/HTTPS 链接")
        if parsed.hostname is None:
            raise FetchError("链接无效")
        host = parsed.hostname
        addresses = cache.get(host)
        if addresses is None:
            addresses = await self._resolve(host)
            cache[host] = addresses
        if not addresses:
            raise FetchError("无法解析主机地址")
        for ip in addresses:
            if self._is_forbidden_ip(ip):
                raise FetchError("链接指向受限地址")

    async def _follow_redirects(
        self,
        session: httpx.AsyncClient,
        method: str,
        url: str,
        headers: dict,
        cache: dict[str, set[str]],
        *,
        stream: bool,
    ) -> tuple[httpx.Response, str]:
        visited: set[str] = {str(httpx.URL(url))}
        current = url
        for _ in range(self.max_redirects):
            await self._assert_safe_destination(current, cache)
            request = session.build_request(method, current, headers=headers)
            response = await session.send(request, stream=stream)
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    if stream:
                        await response.aclose()
                    else:
                        response.close()
                    raise FetchError("重定向缺少目标")
                next_url = urljoin(str(response.request.url), location)
                await self._assert_safe_destination(next_url, cache)
                try:
                    normalized = str(httpx.URL(next_url))
                except httpx.InvalidURL as exc:
                    if stream:
                        await response.aclose()
                    else:
                        response.close()
                    raise FetchError("重定向目标无效") from exc
                if normalized in visited:
                    if stream:
                        await response.aclose()
                    else:
                        response.close()
                    raise FetchError("检测到重定向循环")
                visited.add(normalized)
                if stream:
                    await response.aclose()
                else:
                    response.close()
                current = normalized
                continue
            return response, str(response.request.url)
        raise FetchError("重定向过多")

    def _normalize_type(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return value.split(";", 1)[0].strip().lower()

    def _is_allowed_type(self, value: str) -> bool:
        if not value:
            return True
        if value in {"application/octet-stream"}:
            return True
        return any(value.startswith(prefix) for prefix in ALLOWED_CONTENT_PREFIXES)

    def _extract_filename(self, disposition: Optional[str]) -> Optional[str]:
        if not disposition:
            return None
        _, params = cgi.parse_header(disposition)
        filename = params.get("filename*")
        if filename and filename.lower().startswith("utf-8''"):
            filename = unquote(filename[7:])
        if not filename:
            filename = params.get("filename")
        return filename

    def _guess_filename(self, mime_type: Optional[str]) -> str:
        if mime_type:
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                return f"download{ext}"
        return "download.bin"


class TelegramFetcher(Fetcher):
    def __init__(self, directory: Path, max_size: int, retries: int = 3) -> None:
        self.directory = directory
        self.max_size = max_size
        self.retries = retries

    async def fetch(self, client: Client, message, **kwargs) -> FetchResult:
        reply = message.reply_to_message
        if not reply:
            raise FetchError("请回复包含媒体的消息")
        preferred = kwargs.get("preferred_name")
        attempt = 0
        last_error = None
        final_path: Optional[Path] = None
        temp_path: Optional[Path] = None
        while attempt < self.retries:
            attempt += 1
            target = reply if attempt == 1 else await client.get_messages(reply.chat.id, reply.id)
            media = self._extract_media(target)
            if media is None:
                raise FetchError("未找到可下载的媒体")
            mime_type = getattr(media, "mime_type", None)
            filename = preferred or getattr(media, "file_name", None)
            file_id_str = getattr(media, "file_id", None)
            if not file_id_str:
                raise FetchError("无法获取文件标识")
            file_id_obj = FileId.decode(file_id_str)
            file_size = getattr(media, "file_size", 0) or 0
            base_name = sanitize_filename(filename or self._default_name(file_id_obj, mime_type))
            if final_path is None:
                final_path = unique_path(self.directory, base_name)
                temp_path = final_path.with_suffix(final_path.suffix + ".part")
            existing = await self._prepare_temp(temp_path, file_size)
            offset = existing // (1024 * 1024)
            try:
                size = await self._download_chunks(client, file_id_obj, file_size, temp_path, offset, existing)
                final_mime = mime_type or mimetypes.guess_type(final_path.name)[0]
                await asyncio.to_thread(os.replace, temp_path, final_path)
                return FetchResult(str(final_path), final_path.name, final_mime, size)
            except AuthBytesInvalid:
                last_error = "文件引用已失效"
                await asyncio.sleep(1)
                continue
            except FloodWait as exc:
                wait_seconds = get_floodwait_seconds(exc)
                sleep_seconds = wait_seconds if wait_seconds > 0 else 1
                last_error = f"请求过于频繁，请 {sleep_seconds} 秒后重试"
                await asyncio.sleep(sleep_seconds + (1 if wait_seconds > 0 else 0))
                continue
            except RPCError as exc:
                last_error = str(exc)
                await asyncio.sleep(1)
                continue
            except FetchError as exc:
                if str(exc) == "文件大小超出限制":
                    raise
                last_error = str(exc)
                await asyncio.sleep(1)
                continue
        raise FetchError(last_error or "下载失败")

    def _extract_media(self, message) -> Optional[object]:
        for attr in ("document", "video", "audio", "voice", "photo", "animation", "video_note", "sticker"):
            media = getattr(message, attr, None)
            if media:
                return media
        return None

    def _default_name(self, file_id: FileId, mime_type: Optional[str]) -> str:
        extension = mimetypes.guess_extension(mime_type or "") or ".bin"
        return f"telegram_{file_id.media_id}_{secrets.token_hex(4)}{extension}"

    async def _prepare_temp(self, path: Optional[Path], file_size: int) -> int:
        if path is None:
            raise FetchError("内部错误")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            return 0
        size = path.stat().st_size
        if file_size and size > file_size:
            await asyncio.to_thread(path.unlink)
            return 0
        chunk = 1024 * 1024
        remainder = size % chunk
        if remainder:
            def truncate():
                with open(path, "rb+") as handle:
                    handle.truncate(size - remainder)
                return size - remainder

            size = await asyncio.to_thread(truncate)
        return size

    async def _download_chunks(self, client: Client, file_id: FileId, file_size: int, path: Optional[Path], offset: int, downloaded: int) -> int:
        if path is None:
            raise FetchError("内部错误")
        async with aiofiles.open(path, "ab") as handle:
            async for data in client.get_file(
                file_id,
                file_size,
                0,
                offset,
                progress=self._progress_checker,
                progress_args=(self.max_size,),
            ):
                if not data:
                    continue
                downloaded += len(data)
                if downloaded > self.max_size:
                    raise FetchError("文件大小超出限制")
                await handle.write(data)
        size = os.path.getsize(path)
        if size > self.max_size:
            raise FetchError("文件大小超出限制")
        return size

    @staticmethod
    async def _progress_checker(current: int, total: int, limit: int) -> None:
        if total and total > limit:
            raise FetchError("文件大小超出限制")
        if current > limit:
            raise FetchError("文件大小超出限制")


class YtDlpFetcher(Fetcher):
    def __init__(self, directory: Path, max_size: int) -> None:
        self.directory = directory
        self.max_size = max_size
        self._semaphore = asyncio.Semaphore(YT_DLP_CONCURRENCY)

    async def fetch(self, client: Client, message, **kwargs) -> FetchResult:
        url = kwargs.get("url")
        if not url:
            raise FetchError("缺少下载链接")
        async with self._semaphore:
            temp_dir = Path(tempfile.mkdtemp(dir=self.directory))
            loop = asyncio.get_running_loop()
            try:
                info = await loop.run_in_executor(None, lambda: self._extract_info(url, temp_dir))
                estimate = info.get("filesize") or info.get("filesize_approx")
                if estimate and estimate > self.max_size:
                    raise FetchError("文件大小超出限制")
                path = await loop.run_in_executor(None, lambda: self._download(url, temp_dir))
                if not path or not os.path.exists(path):
                    raise FetchError("下载失败")
                size = os.path.getsize(path)
                if size > self.max_size:
                    raise FetchError("文件大小超出限制")
                final_name = sanitize_filename(os.path.basename(path))
                final_path = unique_path(self.directory, final_name)
                await asyncio.to_thread(os.replace, path, final_path)
                mime_type = mimetypes.guess_type(final_path.name)[0]
                return FetchResult(str(final_path), final_path.name, mime_type, size)
            finally:
                for child in temp_dir.iterdir():
                    with contextlib.suppress(FileNotFoundError):
                        if child.is_file():
                            child.unlink()
                        else:
                            shutil.rmtree(child, ignore_errors=True)
                with contextlib.suppress(FileNotFoundError):
                    temp_dir.rmdir()

    def _extract_info(self, url: str, temp_dir: Path) -> dict:
        options = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        metadata_path = temp_dir / "metadata.json"
        metadata_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        return info

    def _download(self, url: str, temp_dir: Path) -> Optional[str]:
        options = {
            "outtmpl": str(temp_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "ratelimit": YT_DLP_RATE_LIMIT,
            "continuedl": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        candidates = sorted([p for p in temp_dir.glob("*") if p.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)
        return str(candidates[0]) if candidates else None


def _parse_url_argument(message) -> tuple[Optional[str], Optional[str]]:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) <= 1:
        return None, None
    payload = parts[1].strip()
    if not payload:
        return None, None
    if "|" in payload:
        url_part, name_part = payload.split("|", 1)
        return url_part.strip(), name_part.strip()
    return payload, None


async def _handle_fetch(client: Client, message, fetcher: Fetcher, *, url: Optional[str] = None, preferred_name: Optional[str] = None) -> None:
    helper = GoogleDriveHelper(message.from_user.id)
    status = await client.send_message(message.chat.id, "📥 正在准备下载...", reply_to_message_id=message.id)
    result = None
    try:
        result = await fetcher.fetch(client, message, url=url, preferred_name=preferred_name)
        await client.edit_message_text(message.chat.id, status.id, Messages.DOWNLOADED_SUCCESSFULLY.format(result.name, humanbytes(result.size)))
        upload_result = await helper.upload(result.path, result.mime_type)
        await client.edit_message_text(message.chat.id, status.id, upload_result)
    except FetchError as exc:
        await client.edit_message_text(message.chat.id, status.id, f"❗ {exc}")
    except DriveAccessError as exc:
        await client.edit_message_text(message.chat.id, status.id, drive_error_message(exc.code))
    except Exception as exc:
        await client.edit_message_text(message.chat.id, status.id, f"❗ {exc}")
    finally:
        if result and os.path.exists(result.path):
            with contextlib.suppress(Exception):
                os.remove(result.path)


@Client.on_message(filters.private & filters.command(BotCommands.Download) & CustomFilters.auth_users)
async def download_handler(client, message):
    LOGGER.info("download_handler invoked: user=%s text=%r", getattr(message.from_user, "id", None), message.text)
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    if message.reply_to_message and message.reply_to_message.media:
        _, name = _parse_url_argument(message)
        preferred = sanitize_filename(name) if name else None
        fetcher = TelegramFetcher(DOWNLOAD_PATH, MAX_MIRROR_FILE_SIZE)
        await _handle_fetch(client, message, fetcher, preferred_name=preferred)
        return
    url, name = _parse_url_argument(message)
    if not url:
        await client.send_message(message.chat.id, Messages.DOWNLOAD_USAGE)
        return
    preferred = sanitize_filename(name) if name else None
    fetcher = DirectLinkFetcher(DOWNLOAD_PATH, MAX_MIRROR_FILE_SIZE)
    await _handle_fetch(client, message, fetcher, url=url, preferred_name=preferred)


@Client.on_message(filters.private & filters.command(BotCommands.YtDl) & CustomFilters.auth_users)
async def ytdl_handler(client, message):
    LOGGER.info("ytdl_handler invoked: user=%s text=%r", getattr(message.from_user, "id", None), message.text)
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    url, _ = _parse_url_argument(message)
    if not url:
        await client.send_message(message.chat.id, Messages.PROVIDE_YTDL_LINK)
        return
    fetcher = YtDlpFetcher(DOWNLOAD_PATH, MAX_MIRROR_FILE_SIZE)
    await _handle_fetch(client, message, fetcher, url=url)
