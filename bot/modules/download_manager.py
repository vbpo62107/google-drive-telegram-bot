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
from pyrogram.types import CallbackQuery
from pyrogram.errors import AuthBytesInvalid, FloodWait, RPCError
from pyrogram.file_id import FileId

from bot import DOWNLOAD_DIRECTORY, MAX_MIRROR_FILE_SIZE, SUDO_USERS, LOGGER
from bot.config import BotCommands, Messages
from bot.utils.cache import video_cache
from bot.modules.ytdl_quality_selector import (
    YtDlpQualitySelector,
    YTDL_CALLBACK_PREFIX,
)
from bot.utils.messages_utils import render_permission_error, MessageTemplate
from bot.utils.error_codes import get_error_message, get_error_code_by_exception
from bot.helpers.utils import humanbytes, get_floodwait_seconds
from bot.modules.drive_helper import DriveAccessError, drive_error_message
from bot.modules.gdriveTools import GoogleDriveHelper

LOGGER.info("download_manager module loaded, registering handlers...")

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
            raise FetchError(Messages.DOWNLOAD_MISSING_URL)
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
                        raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
                    if mime_type and not self._is_allowed_type(mime_type):
                        raise FetchError(Messages.DOWNLOAD_TYPE_NOT_ALLOWED)
                finally:
                    await head.aclose()
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
                            raise FetchError(Messages.DOWNLOAD_TYPE_NOT_ALLOWED)
                    actual_length = self._parse_length(response.headers.get("Content-Length"))
                    if actual_length and actual_length > self.max_size:
                        raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
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
                                    raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
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
        raise FetchError(Messages.DOWNLOAD_GENERIC_ERROR)

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
            await response.aclose()
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
            raise FetchError(Messages.DOWNLOAD_ONLY_HTTP)
        if parsed.hostname is None:
            raise FetchError(Messages.DOWNLOAD_INVALID_URL)
        host = parsed.hostname
        addresses = cache.get(host)
        if addresses is None:
            addresses = await self._resolve(host)
            cache[host] = addresses
        if not addresses:
            raise FetchError(Messages.DOWNLOAD_RESOLVE_FAILED)
        for ip in addresses:
            if self._is_forbidden_ip(ip):
                raise FetchError(Messages.DOWNLOAD_FORBIDDEN_DEST)

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
                    await response.aclose()
                    raise FetchError(Messages.DOWNLOAD_REDIRECT_NO_TARGET)
                next_url = urljoin(str(response.request.url), location)
                await self._assert_safe_destination(next_url, cache)
                try:
                    normalized = str(httpx.URL(next_url))
                except httpx.InvalidURL as exc:
                    await response.aclose()
                    raise FetchError(Messages.DOWNLOAD_REDIRECT_INVALID) from exc
                if normalized in visited:
                    await response.aclose()
                    raise FetchError(Messages.DOWNLOAD_REDIRECT_LOOP)
                visited.add(normalized)
                await response.aclose()
                current = normalized
                continue
            return response, str(response.request.url)
        raise FetchError(Messages.DOWNLOAD_REDIRECT_TOO_MANY)

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
            raise FetchError(Messages.DOWNLOAD_REPLY_REQUIRED)
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
                raise FetchError(Messages.DOWNLOAD_MEDIA_NOT_FOUND)
            mime_type = getattr(media, "mime_type", None)
            filename = preferred or getattr(media, "file_name", None)
            file_id_str = getattr(media, "file_id", None)
            if not file_id_str:
                raise FetchError(Messages.DOWNLOAD_FILE_ID_MISSING)
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
                last_error = Messages.DOWNLOAD_FILE_REFERENCE_INVALID
                await asyncio.sleep(1)
                continue
            except FloodWait as exc:
                wait_seconds = get_floodwait_seconds(exc)
                sleep_seconds = wait_seconds if wait_seconds > 0 else 1
                last_error = Messages.DOWNLOAD_TOO_MANY_REQUESTS.format(sleep_seconds)
                await asyncio.sleep(sleep_seconds + (1 if wait_seconds > 0 else 0))
                continue
            except RPCError as exc:
                last_error = str(exc)
                await asyncio.sleep(1)
                continue
            except FetchError as exc:
                if str(exc) == Messages.DOWNLOAD_FILE_TOO_LARGE:
                    raise
                last_error = str(exc)
                await asyncio.sleep(1)
                continue
        raise FetchError(last_error or Messages.DOWNLOAD_GENERIC_ERROR)

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
            raise FetchError(Messages.DOWNLOAD_INTERNAL_ERROR)
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
            raise FetchError(Messages.DOWNLOAD_INTERNAL_ERROR)
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
                    raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
                await handle.write(data)
        size = os.path.getsize(path)
        if size > self.max_size:
            raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
        return size

    @staticmethod
    async def _progress_checker(current: int, total: int, limit: int) -> None:
        if total and total > limit:
            raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
        if current > limit:
            raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)


class YtDlpFetcher(Fetcher):
    def __init__(self, directory: Path, max_size: int) -> None:
        self.directory = directory
        self.max_size = max_size
        self._semaphore = asyncio.Semaphore(YT_DLP_CONCURRENCY)

    async def fetch(self, client: Client, message, **kwargs) -> FetchResult:
        url = kwargs.get("url")
        format_id = kwargs.get("format_id")
        if not url:
            raise FetchError(Messages.DOWNLOAD_MISSING_URL)
        async with self._semaphore:
            temp_dir = Path(tempfile.mkdtemp(dir=self.directory))
            loop = asyncio.get_running_loop()
            try:
                LOGGER.info(
                    "YtDlpFetcher starting extraction: url=%s, format_id=%s, temp_dir=%s",
                    url,
                    format_id,
                    temp_dir
                )
                info = await loop.run_in_executor(None, lambda: self._extract_info(url, temp_dir))
                estimate = info.get("filesize") or info.get("filesize_approx")
                LOGGER.info(
                    "Video info extracted: url=%s, estimated_size=%s, title=%s",
                    url,
                    estimate,
                    info.get("title", "unknown")
                )
                if estimate and estimate > self.max_size:
                    LOGGER.warning(
                        "File size exceeds maximum: url=%s, size=%s, max=%s",
                        url,
                        estimate,
                        self.max_size
                    )
                    raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
                LOGGER.info("Starting yt-dlp download: url=%s, format_id=%s", url, format_id)
                path = await loop.run_in_executor(None, lambda: self._download(url, temp_dir, format_id))
                if not path or not os.path.exists(path):
                    LOGGER.error(
                        "Download failed - no file created: url=%s, format_id=%s, path=%s",
                        url,
                        format_id,
                        path
                    )
                    raise FetchError(Messages.DOWNLOAD_GENERIC_ERROR)
                size = os.path.getsize(path)
                LOGGER.info(
                    "Download completed successfully: url=%s, format_id=%s, size=%s, path=%s",
                    url,
                    format_id,
                    size,
                    path
                )
                if size > self.max_size:
                    LOGGER.warning(
                        "Downloaded file size exceeds maximum: url=%s, size=%s, max=%s",
                        url,
                        size,
                        self.max_size
                    )
                    raise FetchError(Messages.DOWNLOAD_FILE_TOO_LARGE)
                final_name = sanitize_filename(os.path.basename(path))
                final_path = unique_path(self.directory, final_name)
                await asyncio.to_thread(os.replace, path, final_path)
                mime_type = mimetypes.guess_type(final_path.name)[0]
                return FetchResult(str(final_path), final_path.name, mime_type, size)
            except Exception as e:
                LOGGER.error(
                    "YtDlpFetcher encountered error: url=%s, format_id=%s, error=%s",
                    url,
                    format_id,
                    str(e),
                    exc_info=True
                )
                raise
            finally:
                LOGGER.debug("Cleaning up temporary directory: %s", temp_dir)
                for child in temp_dir.iterdir():
                    with contextlib.suppress(FileNotFoundError):
                        if child.is_file():
                            child.unlink()
                        else:
                            shutil.rmtree(child, ignore_errors=True)
                with contextlib.suppress(FileNotFoundError):
                    temp_dir.rmdir()
                LOGGER.debug("Temporary directory cleanup completed: %s", temp_dir)

    def _extract_info(self, url: str, temp_dir: Path) -> dict:
        LOGGER.debug("Extracting video info using yt-dlp: url=%s", url)
        options = {
            "cookiefile": "/app/cookies.txt",
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
            LOGGER.info(
                "yt-dlp info extraction successful: url=%s, title=%s, formats_count=%d",
                url,
                info.get("title", "unknown"),
                len(info.get("formats", []))
            )
        except Exception as e:
            LOGGER.error(
                "yt-dlp info extraction failed: url=%s, error=%s",
                url,
                str(e),
                exc_info=True
            )
            raise
        metadata_path = temp_dir / "metadata.json"
        metadata_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.debug("Metadata saved to: %s", metadata_path)
        return info

    def _download(self, url: str, temp_dir: Path, format_id: Optional[str]) -> Optional[str]:
        LOGGER.info(
            "Starting yt-dlp download: url=%s, format_id=%s, temp_dir=%s",
            url,
            format_id,
            temp_dir
        )
        format_selector = None
        if format_id:
            format_selector = "bestaudio" if format_id == "audio" else format_id
            LOGGER.debug(
                "Format selector determined: format_id=%s, format_selector=%s",
                format_id,
                format_selector
            )
        options = {
            "cookiefile": "/app/cookies.txt",
            "outtmpl": str(temp_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "ratelimit": YT_DLP_RATE_LIMIT,
            "continuedl": True,
        }
        if format_selector:
            options["format"] = format_selector
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                LOGGER.info(
                    "yt-dlp download successful: url=%s, format_id=%s, title=%s",
                    url,
                    format_id,
                    info.get("title", "unknown")
                )
        except Exception as e:
            LOGGER.error(
                "yt-dlp download failed: url=%s, format_id=%s, error=%s",
                url,
                format_id,
                str(e),
                exc_info=True
            )
            raise
        candidates = sorted([p for p in temp_dir.glob("*") if p.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)
        if candidates:
            result = str(candidates[0])
            LOGGER.debug(
                "Download file located: url=%s, format_id=%s, file=%s",
                url,
                format_id,
                result
            )
            return result
        LOGGER.warning(
            "No download file found in temp directory: url=%s, format_id=%s, temp_dir=%s",
            url,
            format_id,
            temp_dir
        )
        return None


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


async def _handle_fetch(
    client: Client,
    message,
    fetcher: Fetcher,
    *,
    url: Optional[str] = None,
    preferred_name: Optional[str] = None,
    format_id: Optional[str] = None,
) -> None:
    """Handle file fetching, uploading, and user feedback."""
    user_id = getattr(message.from_user, "id", None)

    # 认证检查
    from bot.helpers.sql_helper.gDriveDB import is_authorized
    if not is_authorized(str(user_id)):
        await client.send_message(
            message.chat.id,
            Messages.NOT_AUTH,
            reply_to_message_id=message.id
        )
        LOGGER.warning("Unauthorized fetch attempt: user=%s", user_id)
        return

    helper = GoogleDriveHelper(user_id)
    status = await client.send_message(
        message.chat.id, Messages.DOWNLOAD_PREPARING, reply_to_message_id=message.id
    )
    result = None

    try:
        # 开始下载
        LOGGER.info("Starting fetch: user=%s, fetcher=%s", user_id, type(fetcher).__name__)
        result = await fetcher.fetch(
            client, message, url=url, preferred_name=preferred_name, format_id=format_id
        )
        LOGGER.info(
            "Fetch completed: user=%s, file=%s, size=%d bytes",
            user_id,
            result.name,
            result.size,
        )

        # 发送下载完成消息
        await client.edit_message_text(
            message.chat.id,
            status.id,
            Messages.DOWNLOADED_SUCCESSFULLY.format(
                filename=result.name,
                size=humanbytes(result.size),
            ),
        )

        # 开始上传
        LOGGER.info(
            "Starting upload: user=%s, file=%s, mime_type=%s, path=%s",
            user_id,
            result.name,
            result.mime_type,
            result.path,
        )
        try:
            upload_result = await helper.upload(result.path, result.mime_type)
        except Exception as upload_exc:
            error_msg = Messages.DOWNLOAD_FAILED.format(str(upload_exc))
            LOGGER.error(
                "Upload exception occurred: user=%s, file=%s, exception=%s",
                user_id,
                result.name,
                str(upload_exc),
                exc_info=True,
            )
            await client.edit_message_text(message.chat.id, status.id, error_msg)
            raise

        # 记录上传结果的类型和内容
        LOGGER.info(
            "Upload completed: user=%s, file=%s, result_type=%s, result_value=%r",
            user_id,
            result.name,
            type(upload_result).__name__,
            upload_result,
        )

        # 类型检查：确保 upload_result 是字符串
        if not isinstance(upload_result, str):
            LOGGER.warning(
                "Upload result is not string: user=%s, expected=str, got=%s, value=%r. Converting to string...",
                user_id,
                type(upload_result).__name__,
                upload_result,
            )
            upload_result = str(upload_result)

        # 检查返回字符串是否包含错误信息
        if "ERROR" in upload_result or "error" in upload_result.lower():
            LOGGER.error(
                "Upload returned error message: user=%s, file=%s, error_message=%s",
                user_id,
                result.name,
                upload_result,
            )
            await client.edit_message_text(message.chat.id, status.id, upload_result)
            LOGGER.info(
                "Error message sent to user: user=%s, file=%s",
                user_id,
                result.name,
            )
        else:
            # 上传成功，发送成功消息给用户
            await client.edit_message_text(message.chat.id, status.id, upload_result)
            LOGGER.info(
                "Success message sent to user: user=%s, file=%s, message_length=%d",
                user_id,
                result.name,
                len(upload_result),
            )

    except FetchError as exc:
        error_code = get_error_code_by_exception(exc)
        error_msg = get_error_message(error_code, str(exc))
        LOGGER.error("FetchError for user=%s: %s", user_id, str(exc), exc_info=True)
        await client.edit_message_text(message.chat.id, status.id, error_msg)

    except DriveAccessError as exc:
        error_msg = drive_error_message(exc.code)
        LOGGER.error(
            "DriveAccessError for user=%s (code=%s): %s",
            user_id,
            exc.code,
            str(exc),
            exc_info=True,
        )
        await client.edit_message_text(message.chat.id, status.id, error_msg)

    except Exception as exc:
        error_code = get_error_code_by_exception(exc)
        error_msg = get_error_message(error_code, str(exc))
        LOGGER.exception("Unexpected error for user=%s: %s", user_id, str(exc))
        await client.edit_message_text(message.chat.id, status.id, error_msg)

    finally:
        # 清理临时文件
        if result and os.path.exists(result.path):
            LOGGER.info("Cleaning up temporary file: %s", result.path)
            with contextlib.suppress(Exception):
                os.remove(result.path)
            LOGGER.info("Temporary file removed: %s", result.path)


@Client.on_message(filters.private & filters.command(["download", "dl"]), group=-1)
async def download_handler(client, message):
    LOGGER.critical("🔥🔥🔥 download_handler TRIGGERED 🔥🔥🔥")
    LOGGER.info(
        "download_handler triggered: user=%s text=%r",
        getattr(message.from_user, "id", "NO_USER"),
        message.text,
    )
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        msg = render_permission_error("此命令", "使用")
        await client.send_message(message.chat.id, msg)
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


@Client.on_message(filters.private & filters.command(["ytdl"]), group=-1)
async def ytdl_handler(client, message):
    LOGGER.critical("🔥🔥🔥 ytdl_handler ABSOLUTELY TRIGGERED 🔥🔥🔥")
    LOGGER.info(
        "ytdl_handler triggered: user=%s text=%r",
        getattr(message.from_user, "id", "NO_USER"),
        message.text,
    )
    if message.from_user is None:
        LOGGER.warning(
            "ytdl_handler invoked without from_user: chat_id=%s text=%r",
            message.chat.id,
            message.text,
        )
        return
    user_id = message.from_user.id
    LOGGER.info("Checking permissions: user=%s", user_id)
    if user_id not in SUDO_USERS:
        LOGGER.info("ytdl_handler permission denied for user=%s", user_id)
        msg = render_permission_error("此命令", "使用")
        await client.send_message(message.chat.id, msg)
        return

    # 认证检查
    from bot.helpers.sql_helper.gDriveDB import is_authorized
    if not is_authorized(str(user_id)):
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        LOGGER.warning("Unauthorized ytdl attempt: user=%s", user_id)
        return

    url, _ = _parse_url_argument(message)
    if not url:
        LOGGER.info("No URL provided, sending help message")
        await client.send_message(message.chat.id, Messages.PROVIDE_YTDL_LINK)
        return

    # 【新値】显示准备中消息
    preparing_msg = await client.send_message(
        message.chat.id,
        Messages.DOWNLOAD_PREPARING,
        reply_to_message_id=message.id
    )
    
    LOGGER.info("Starting YtDlp analysis for URL: %s", url)
    
    try:
        # 【新値】获取视频信息（不直接下载）
        loop = asyncio.get_running_loop()
        fetcher = YtDlpFetcher(DOWNLOAD_PATH, MAX_MIRROR_FILE_SIZE)
        
        LOGGER.debug("Extracting video information: url=%s, user_id=%s", url, user_id)
        info = await loop.run_in_executor(
            None,
            lambda: fetcher._extract_info(url, DOWNLOAD_PATH)
        )
        
        video_title = info.get('title', 'Unknown Video')
        LOGGER.info("Video info extracted: title=%s, url=%s, user_id=%s", video_title, url, user_id)
        
        # 【新値】删除准备中的消息
        try:
            await client.delete_messages(message.chat.id, preparing_msg.id)
            LOGGER.debug("Preparing message deleted: user_id=%s", user_id)
        except Exception as e:
            LOGGER.warning("Failed to delete preparing message: user_id=%s, error=%s", user_id, e)
        
        # 【新値】缓存视频信息
        video_cache.set(user_id, {
            'url': url,
            'info': info,
            'title': video_title
        })
        LOGGER.info("Video info cached for user: user_id=%s, title=%s", user_id, video_title)
        
        # 【新値】显示清晰度选择界面
        LOGGER.info("Displaying quality selector: user_id=%s, title=%s", user_id, video_title)
        await YtDlpQualitySelector.show_quality_selector(
            client, message, info, video_title
        )
        
    except Exception as exc:
        LOGGER.error("Error in ytdl analysis: user_id=%s, url=%s, error=%s", user_id, url, str(exc), exc_info=True)
        try:
            await client.delete_messages(message.chat.id, preparing_msg.id)
        except Exception:
            pass

        error_code = get_error_code_by_exception(exc)
        error_msg = get_error_message(error_code, str(exc))
        await client.send_message(message.chat.id, error_msg)


@Client.on_callback_query(filters=filters.regex(rf"^{YTDL_CALLBACK_PREFIX}"))
async def handle_ytdl_quality_selection(
    client: Client, callback_query: CallbackQuery
) -> None:
    """处理 ytdl 清晰度选择回调"""

    user_id = callback_query.from_user.id
    selected_format = callback_query.data.replace(YTDL_CALLBACK_PREFIX, "")

    LOGGER.info(
        "handle_ytdl_quality_selection: Callback triggered, data=%s, user=%s, format=%s",
        callback_query.data,
        user_id,
        selected_format,
    )

    try:
        await callback_query.answer("📥 开始下载...", show_alert=False)

        cached = video_cache.get(user_id)
        if not cached:
            LOGGER.warning("handle_ytdl_quality_selection: Cache miss for user %s", user_id)
            await callback_query.answer(
                "❌ 视频信息已过期，请重新发送链接",
                show_alert=True
            )
            return

        url = cached['url']
        video_title = cached.get('title', 'Unknown')

        LOGGER.info(
            "handle_ytdl_quality_selection: Retrieved cached info for user %s, title=%s",
            user_id,
            video_title,
        )

        message = callback_query.message
        status_text = (
            f"📥 **开始下载**\n"
            f"视频：`{video_title[:30]}...`\n"
            f"清晰度：{selected_format}\n\n"
            f"⏳ 正在下载..."
        )

        try:
            await client.edit_message_text(
                message.chat.id,
                message.id,
                status_text
            )
            LOGGER.info("handle_ytdl_quality_selection: Status message updated")
        except Exception as edit_exc:
            LOGGER.warning("handle_ytdl_quality_selection: Failed to edit message: %s", edit_exc)

        fetcher = YtDlpFetcher(DOWNLOAD_PATH, MAX_MIRROR_FILE_SIZE)

        LOGGER.info(
            "handle_ytdl_quality_selection: Starting _handle_fetch for user %s with format %s",
            user_id,
            selected_format,
        )
        await _handle_fetch(client, message, fetcher, url=url, format_id=selected_format)

        video_cache.clear(user_id)
        LOGGER.info("handle_ytdl_quality_selection: Cache cleared for user %s", user_id)

    except Exception as exc:
        LOGGER.error("handle_ytdl_quality_selection: Error occurred - %s", str(exc), exc_info=True)
        error_msg = f"❌ **下载失败**\n\n错误: {str(exc)[:100]}"
        try:
            await callback_query.answer(error_msg, show_alert=True)
        except Exception as answer_exc:
            LOGGER.error("handle_ytdl_quality_selection: Failed to answer callback: %s", answer_exc)
