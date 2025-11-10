import asyncio
import os
import re
import time

import aiofiles
import aiohttp
from pyrogram import Client, filters
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential

from bot import DOWNLOAD_DIRECTORY, SUDO_USERS
from bot.config import Messages
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import extract_filename_from_url, format_bytes, format_elapsed_eta, format_speed, render_progress_bar
from bot.modules.drive_helper import get_drive_instance


@Client.on_message(filters.command("mirror") & filters.private)
async def mirror_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    if not message.text or len(message.text.split(maxsplit=1)) < 2:
        await client.send_message(message.chat.id, "❌ 请提供直链 URL.")
        return
    url = message.text.split(maxsplit=1)[1].strip()
    if not re.match(r"^https?://", url, re.I):
        await client.send_message(message.chat.id, "❌ 仅支持 HTTP(S) 链接.")
        return
    creds = gDriveDB.search(message.from_user.id)
    if not creds:
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    filename = extract_filename_from_url(url, "downloaded_file")
    os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
    base, ext = os.path.splitext(filename)
    counter = 1
    destination = os.path.join(DOWNLOAD_DIRECTORY, filename)
    temp_path = destination + ".part"
    while os.path.exists(destination) or os.path.exists(temp_path):
        filename = f"{base}_{counter}{ext}"
        destination = os.path.join(DOWNLOAD_DIRECTORY, filename)
        temp_path = destination + ".part"
        counter += 1
    status = await client.send_message(message.chat.id, f"📥 开始处理 `{filename}`")
    download_start = time.monotonic()
    last_download_update = 0.0
    total_size = 0
    downloaded = 0

    async def update_progress(stage, emoji, transferred, total, elapsed, link=None):
        percent = (transferred / total * 100) if total else 0
        bar = render_progress_bar(transferred, total)
        total_text = format_bytes(total) if total else "未知大小"
        speed_value = transferred / elapsed if elapsed > 0 else 0
        speed_text = format_speed(speed_value)
        elapsed_text, eta_text = format_elapsed_eta(elapsed, transferred, total)
        progress_lines = [
            f"{emoji} {stage}",
            f"{bar} {percent:.2f}%",
            f"☁️ {format_bytes(transferred)} / {total_text}",
            f"📄 `{filename}`",
            f"🔗 {link if link else url}",
            f"⚡ {speed_text}",
            f"⏱️ {elapsed_text}",
            f"⏳ {eta_text}",
        ]
        await status.edit_text("\n".join(progress_lines))

    async def download_once():
        nonlocal total_size, downloaded, download_start, last_download_update
        download_start = time.monotonic()
        last_download_update = 0.0
        downloaded = 0
        if os.path.exists(temp_path):
            await asyncio.to_thread(os.remove, temp_path)
        timeout = aiohttp.ClientTimeout(total=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    raise ValueError(f"HTTP {response.status}")
                length = response.headers.get("Content-Length")
                try:
                    total_size = int(length) if length else 0
                except ValueError:
                    total_size = 0
                await update_progress("下载中", "📥", 0, total_size, 0)
                async with aiofiles.open(temp_path, "wb") as file:
                    async for chunk in response.content.iter_chunked(1024 * 64):
                        if not chunk:
                            continue
                        await file.write(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        elapsed = now - download_start
                        if downloaded == total_size or now - last_download_update >= 1.5:
                            last_download_update = now
                            await update_progress("下载中", "📥", downloaded, total_size, elapsed)
                if downloaded:
                    await update_progress("下载中", "📥", downloaded, total_size, time.monotonic() - download_start)
        await asyncio.to_thread(os.replace, temp_path, destination)

    async def download_file():
        retryer = AsyncRetrying(wait=wait_exponential(multiplier=4, min=4, max=16), stop=stop_after_attempt(3),
            retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, ValueError)), reraise=False)
        try:
            async for attempt in retryer:
                with attempt:
                    await download_once()
                    return
        except RetryError as err:
            raise err

    drive = await get_drive_instance(message.from_user.id)
    upload_start = 0.0
    last_upload_update = 0.0

    async def upload_callback(transferred, total):
        nonlocal upload_start, last_upload_update
        if not upload_start:
            upload_start = time.monotonic()
        now = time.monotonic()
        elapsed = now - upload_start
        if transferred < total and now - last_upload_update < 1.5:
            return
        last_upload_update = now
        await update_progress("上传中", "☁️", transferred, total, elapsed)

    try:
        await download_file()
        upload_start = time.monotonic()
        upload_total = total_size or await asyncio.to_thread(os.path.getsize, destination)
        await update_progress("准备上传", "☁️", 0, upload_total, 0)
        upload_result = await drive.upload_file_with_progress(destination, progress_callback=upload_callback)
        if upload_result.startswith("✅"):
            await status.edit_text(upload_result)
        elif upload_result.startswith("❗") or upload_result.startswith("**ERROR"):
            await status.edit_text(upload_result)
        else:
            await status.edit_text(f"❌ {upload_result}")
    except RetryError:
        await status.edit_text("🔁 重试多次后仍失败")
    except Exception as exc:
        await status.edit_text(f"❌ {str(exc)}")
    finally:
        if os.path.exists(temp_path):
            try:
                await asyncio.to_thread(os.remove, temp_path)
            except FileNotFoundError:
                pass
        if os.path.exists(destination):
            try:
                await asyncio.to_thread(os.remove, destination)
            except FileNotFoundError:
                pass
