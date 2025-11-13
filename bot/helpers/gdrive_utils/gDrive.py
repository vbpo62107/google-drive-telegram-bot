import asyncio
import contextlib
import hashlib
import inspect
import json
import logging
import os
import re
import threading
import time
import urllib.parse as urlparse
from mimetypes import guess_type
from typing import Any, Callable, Optional
from urllib.parse import parse_qs

from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tenacity import RetryError, Retrying, before_log, retry_if_exception, stop_after_attempt
from tenacity.wait import wait_random_exponential

from bot import LOGGER, SERVICE_ACCOUNT_GRANT_ACCESS
from bot.config import Messages
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import format_bytes, humanbytes


class AdaptiveChunkController:
    _BASE_UNIT = 256 * 1024

    def __init__(
        self,
        min_size=8 * 1024 * 1024,
        max_size=32 * 1024 * 1024,
        step=4 * 1024 * 1024,
        initial_size: Optional[int] = None,
    ):
        self._min = self._align_value(min_size)
        self._max = self._align_value(max_size)
        self._step = max(self._BASE_UNIT, self._align_value(step))
        start_value = initial_size if initial_size is not None else self._min
        self._current = self._align_value(start_value)
        if self._current < self._min:
            self._current = self._min
        if self._current > self._max:
            self._current = self._max
        self._success_streak = 0
        self._failure_streak = 0

    def _align_value(self, value: int) -> int:
        value = max(value, self._BASE_UNIT)
        return (value // self._BASE_UNIT) * self._BASE_UNIT

    @property
    def current_size(self) -> int:
        return self._current

    def _set_current(self, value: int) -> None:
        aligned = self._align_value(value)
        if aligned < self._min:
            aligned = self._min
        if aligned > self._max:
            aligned = self._max
        self._current = aligned

    def apply_to(self, media) -> None:
        media.chunksize = self._align_value(self._current)

    def record_success(self) -> int:
        self._success_streak += 1
        self._failure_streak = 0
        if self._success_streak >= 2 and self._current < self._max:
            self._set_current(self._current + self._step)
            self._success_streak = 0
        return self._current

    def record_failure(self) -> int:
        self._failure_streak += 1
        self._success_streak = 0
        if self._failure_streak >= 1 and self._current > self._min:
            self._set_current(self._current - self._step)
            self._failure_streak = 0
        return self._current


logging.getLogger("googleapiclient.discovery").setLevel(logging.ERROR)


class GoogleDrive:
    def __init__(
        self,
        *,
        user_id: int,
        credentials,
        parent_id: Optional[str],
        mode: str,
        fingerprint: Optional[str],
    ) -> None:
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self._user_id = user_id
        self._mode = mode
        self._fingerprint = fingerprint
        self.__parent_id = parent_id or "root"
        self.__service = self.authorize(credentials)
        self._retryer = self._build_retryer()
        self._preferred_chunk_size = 8 * 1024 * 1024
        self._active_chunk_controller: Optional[AdaptiveChunkController] = None
        if self._mode == "service_account" and SERVICE_ACCOUNT_GRANT_ACCESS:
            self._ensure_service_account_permissions(credentials)

    def _build_retryer(self) -> Retrying:
        return Retrying(
            wait=wait_random_exponential(multiplier=2, max=30),
            stop=stop_after_attempt(5),
            retry=retry_if_exception(self._should_retry_exception),
            before=before_log(LOGGER, logging.DEBUG),
            reraise=True,
        )

    def _should_retry_exception(self, exc: BaseException) -> bool:
        if isinstance(exc, HttpError):
            status = getattr(exc.resp, "status", None)
            if status in (401, 403, 429):
                return True
            if status and status >= 500:
                return True
            try:
                details = json.loads(exc.content).get("error", {}).get("errors", []) if exc.content else []
            except Exception:
                details = []
            for item in details:
                reason = item.get("reason")
                if reason in {"rateLimitExceeded", "userRateLimitExceeded", "backendError", "dailyLimitExceeded"}:
                    return True
        if isinstance(exc, (RefreshError, TransportError)):
            return True
        return False

    def _record_failure(self, exc: BaseException) -> None:
        if self._should_retry_exception(exc):
            gDriveDB.mark_failure(self._user_id)

    def _reset_failures(self) -> None:
        gDriveDB.reset_failures(self._user_id)

    def _start_upload_session(self) -> AdaptiveChunkController:
        controller = AdaptiveChunkController(initial_size=self._preferred_chunk_size)
        self._active_chunk_controller = controller
        return controller

    def _finish_upload_session(self) -> None:
        if self._active_chunk_controller is not None:
            self._preferred_chunk_size = self._active_chunk_controller.current_size
        self._active_chunk_controller = None

    def _get_upload_state_path(self, file_path: str) -> str:
        return f"{file_path}.upload_state"

    def _load_upload_state(
        self,
        file_path: str,
        expected_size: Optional[int] = None,
        expected_md5: Optional[str] = None,
    ):
        path = self._get_upload_state_path(file_path)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            LOGGER.debug("Failed to read upload state for %s", file_path, exc_info=True)
            self._clear_upload_state(file_path)
            return None
        if not isinstance(data, dict):
            self._clear_upload_state(file_path)
            return None
        session_uri = data.get("session_uri")
        progress = data.get("progress")
        stored_size = data.get("total_size")
        if expected_size is not None and stored_size not in (None, expected_size):
            LOGGER.info("Discarding upload state for %s because file size changed", file_path)
            self._clear_upload_state(file_path)
            return None
        stored_md5 = data.get("md5")
        if expected_md5 is not None:
            if not stored_md5 or stored_md5 != expected_md5:
                LOGGER.info("Discarding upload state for %s because checksum changed", file_path)
                self._clear_upload_state(file_path)
                return None
        if not session_uri or not isinstance(session_uri, str):
            self._clear_upload_state(file_path)
            return None
        if not isinstance(progress, (int, float)):
            self._clear_upload_state(file_path)
            return None
        data["progress"] = int(progress)
        if "range_start" in data:
            try:
                data["range_start"] = int(data["range_start"])
            except Exception:
                data.pop("range_start", None)
        if "range_end" in data:
            try:
                data["range_end"] = int(data["range_end"])
            except Exception:
                data.pop("range_end", None)
        if "chunk_size" in data:
            try:
                data["chunk_size"] = int(data["chunk_size"])
            except Exception:
                data.pop("chunk_size", None)
        return data

    def _save_upload_state(
        self,
        file_path: str,
        *,
        session_uri: str,
        progress: int,
        chunk_size: int,
        range_start: int,
        total_size: int,
        checksum: Optional[str] = None,
    ) -> None:
        if not session_uri:
            return
        path = self._get_upload_state_path(file_path)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        data = {
            "session_uri": session_uri,
            "progress": int(progress),
            "chunk_size": int(chunk_size) if chunk_size else chunk_size,
            "range_start": int(range_start),
            "range_end": int(progress),
            "total_size": int(total_size),
            "updated_at": time.time(),
        }
        if checksum:
            data["md5"] = checksum
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp_path, path)
        except Exception:
            LOGGER.debug("Failed to persist upload state for %s", file_path, exc_info=True)
            with contextlib.suppress(OSError):
                os.remove(tmp_path)

    def _clear_upload_state(self, file_path: str) -> None:
        path = self._get_upload_state_path(file_path)
        try:
            os.remove(path)
        except FileNotFoundError:
            return
        except Exception:
            LOGGER.debug("Failed to remove upload state for %s", file_path, exc_info=True)

    def _call(self, func: Callable[[], Any]):
        try:
            result = self._retryer(func)
            self._reset_failures()
            return result
        except RetryError as err:
            exc = err.last_attempt.exception()
            if exc:
                self._record_failure(exc)
                raise exc
            raise
        except Exception as exc:
            self._record_failure(exc)
            raise

    def _compute_file_md5(self, file_path: str) -> Optional[str]:
        try:
            digest = hashlib.md5()
            with open(file_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except Exception:
            LOGGER.debug("Failed to compute MD5 for %s", file_path, exc_info=True)
            return None

    def _verify_remote_checksum(
        self, file_id: Optional[str], local_md5: Optional[str], filename: str
    ) -> Optional[str]:
        if not file_id or not local_md5:
            return None
        try:
            metadata = self._call(
                lambda: self.__service.files()
                .get(
                    fileId=file_id,
                    fields="md5Checksum,headRevisionId",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            LOGGER.error("Failed to verify checksum for %s", file_id, exc_info=True)
            return f"**ERROR:** ```{str(exc).replace('>', '').replace('<', '')}```"
        remote_md5 = metadata.get("md5Checksum")
        if remote_md5 and remote_md5 != local_md5:
            try:
                self._call(
                    lambda: self.__service.files()
                    .delete(fileId=file_id, supportsAllDrives=True)
                    .execute()
                )
            except Exception:
                LOGGER.error("Failed to delete file %s after checksum mismatch", file_id, exc_info=True)
            return Messages.CHECKSUM_MISMATCH.format(filename)
        return None

    def _wait_if_paused(
        self,
        pause_event: Optional[threading.Event],
        cancel_callback: Optional[Callable[[], bool]],
    ) -> None:
        if pause_event is None:
            return
        while not pause_event.is_set():
            if cancel_callback and cancel_callback():
                raise RuntimeError("cancelled")
            time.sleep(0.2)

    def _perform_chunked_upload(
        self,
        request,
        controller: Optional[AdaptiveChunkController],
        *,
        on_progress: Optional[Callable[[int], None]] = None,
        pause_event: Optional[threading.Event] = None,
        cancel_callback: Optional[Callable[[], bool]] = None,
        on_chunk_success: Optional[Callable[[int, Any, Any], None]] = None,
    ):
        controller = controller or self._active_chunk_controller
        if controller is None:
            raise RuntimeError("Missing upload controller")
        media = getattr(request, "resumable", None) or getattr(request, "resumable_media", None)
        if media is None:
            media = getattr(request, "media_body", None)
        if media is None:
            raise RuntimeError("Invalid upload request")
        controller.apply_to(media)
        response = None
        while response is None:
            if cancel_callback and cancel_callback():
                raise RuntimeError("cancelled")
            self._wait_if_paused(pause_event, cancel_callback)
            try:
                status, response = request.next_chunk()
                controller.record_success()
                self._preferred_chunk_size = controller.current_size
                if cancel_callback and cancel_callback():
                    raise RuntimeError("cancelled")
                if status and on_progress:
                    on_progress(int(status.resumable_progress))
                if status and on_chunk_success:
                    on_chunk_success(int(status.resumable_progress), request, media)
                if response is None:
                    controller.apply_to(media)
            except Exception as exc:
                if isinstance(exc, RuntimeError) and str(exc) == "cancelled":
                    raise
                controller.record_failure()
                self._preferred_chunk_size = controller.current_size
                controller.apply_to(media)
                raise
        return response

    def _ensure_service_account_permissions(self, credentials) -> None:
        if self.__parent_id == "root":
            return
        email = getattr(credentials, "service_account_email", None)
        if not email:
            return
        body = {
            "type": "user",
            "role": "writer",
            "emailAddress": email,
        }
        try:
            self._call(
                lambda: self.__service.permissions()
                .create(
                    fileId=self.__parent_id,
                    body=body,
                    supportsAllDrives=True,
                    sendNotificationEmail=False,
                )
                .execute()
            )
        except HttpError as err:
            try:
                payload = json.loads(err.content)
                reason = payload.get("error", {}).get("errors", [{}])[0].get("reason")
            except Exception:
                reason = None
            if reason != "alreadyExists":
                LOGGER.warning("Failed to grant service account access to %s: %s", self.__parent_id, err)

    def getIdFromUrl(self, link: str):
        if "folders" in link or "file" in link:
            regex = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"
            res = re.search(regex, link)
            if res is None:
                raise IndexError("GDrive ID not found.")
            return res.group(5)
        parsed = urlparse.urlparse(link)
        return parse_qs(parsed.query)["id"][0]

    def search_files(self, query, page_token=None):
        sanitized = query.replace("'", "\\'")
        params = {
            "q": f"name contains '{sanitized}'",
            "spaces": "drive",
            "corpora": "allDrives",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "pageSize": 20,
            "fields": "nextPageToken, files(id, name, mimeType, size)",
        }
        if page_token:
            params["pageToken"] = page_token
        return self._call(lambda: self.__service.files().list(**params).execute())

    def getFilesByFolderId(self, folder_id):
        page_token = None
        q = f"'{folder_id}' in parents"
        files = []
        while True:
            params = {
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
                "q": q,
                "spaces": "drive",
                "pageSize": 200,
                "fields": "nextPageToken, files(id, name, mimeType,size)",
            }
            if page_token:
                params["pageToken"] = page_token
            response = self._call(lambda: self.__service.files().list(**params).execute())
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if page_token is None:
                break
        return files

    def copyFile(self, file_id, dest_id):
        body = {"parents": [dest_id]}
        try:
            return self._call(
                lambda: self.__service.files()
                .copy(supportsAllDrives=True, fileId=file_id, body=body)
                .execute()
            )
        except HttpError as err:
            if err.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(err.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if reason == "dailyLimitExceeded":
                    raise IndexError("LimitExceeded")
            raise

    def cloneFolder(self, name, local_path, folder_id, parent_id):
        files = self.getFilesByFolderId(folder_id)
        new_id = None
        if len(files) == 0:
            return self.__parent_id
        for file in files:
            if file.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                file_path = os.path.join(local_path, file.get("name"))
                current_dir_id = self.create_directory(file.get("name"))
                new_id = self.cloneFolder(file.get("name"), file_path, file.get("id"), current_dir_id)
            else:
                try:
                    self.transferred_size += int(file.get("size"))
                except (TypeError, ValueError):
                    pass
                try:
                    self.copyFile(file.get("id"), parent_id)
                    new_id = parent_id
                except Exception as err:
                    return err
        return new_id

    def create_directory(self, directory_name):
        file_metadata = {
            "name": directory_name,
            "mimeType": self.__G_DRIVE_DIR_MIME_TYPE,
            "parents": [self.__parent_id],
        }
        file = self._call(
            lambda: self.__service.files()
            .create(supportsAllDrives=True, body=file_metadata)
            .execute()
        )
        return file.get("id")

    def clone(self, link):
        self.transferred_size = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return Messages.INVALID_GDRIVE_URL
        try:
            meta = self._call(
                lambda: self.__service.files()
                .get(
                    supportsAllDrives=True,
                    fileId=file_id,
                    fields="name,id,mimeType,size",
                )
                .execute()
            )
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.create_directory(meta.get("name"))
                result = self.cloneFolder(meta.get("name"), meta.get("name"), meta.get("id"), dir_id)
                return Messages.COPIED_SUCCESSFULLY.format(
                    meta.get("name"),
                    self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id),
                    humanbytes(self.transferred_size),
                )
            file = self.copyFile(meta.get("id"), self.__parent_id)
            return Messages.COPIED_SUCCESSFULLY.format(
                file.get("name"),
                self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get("id")),
                humanbytes(int(meta.get("size", 0))),
            )
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info("Total Attempts: %s", err.last_attempt.attempt_number)
                err = err.last_attempt.exception()
            err = str(err).replace(">", "").replace("<", "")
            LOGGER.error(err)
            return f"**ERROR:** ```{err}```"

    def upload_file(self, file_path, mimeType=None):
        mime_type = mimeType if mimeType else guess_type(file_path)[0]
        mime_type = mime_type if mime_type else "text/plain"
        controller = self._start_upload_session()
        filename = os.path.basename(file_path)
        filesize = humanbytes(os.path.getsize(file_path))
        local_md5 = self._compute_file_md5(file_path)
        body = {
            "name": filename,
            "description": "Uploaded using @UploadGdriveBot",
            "mimeType": mime_type,
            "parents": [self.__parent_id],
        }
        LOGGER.info("Upload: %s", file_path)
        try:
            media_body = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                chunksize=controller.current_size,
                resumable=True,
            )
            request = self.__service.files().create(
                body=body,
                media_body=media_body,
                fields="id",
                supportsAllDrives=True,
            )

            def perform():
                return self._perform_chunked_upload(request, controller)

            uploaded_file = self._call(perform)
            file_id = uploaded_file.get("id")
            checksum_error = self._verify_remote_checksum(file_id, local_md5, filename)
            if checksum_error:
                return checksum_error
            return Messages.UPLOADED_SUCCESSFULLY.format(
                filename,
                self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file_id),
                filesize,
            )
        except HttpError as err:
            status = getattr(err.resp, "status", None)
            session_not_found_statuses = {404, 410}
            session_not_found_reasons = {"resumableNotFound"}
            if err.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(err.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if reason in {"userRateLimitExceeded", "dailyLimitExceeded"}:
                    return Messages.RATE_LIMIT_EXCEEDED_MESSAGE
                if reason in session_not_found_reasons or status in session_not_found_statuses:
                    self._clear_upload_state(file_path)
                return f"**ERROR:** {reason}"
            if status in session_not_found_statuses:
                self._clear_upload_state(file_path)
            return f"**ERROR:** ```{str(err).replace('>', '').replace('<', '')}```"
        except Exception as e:
            return f"**ERROR:** ```{e}```"
        finally:
            self._finish_upload_session()

    async def upload_file_with_progress(
        self,
        file_path,
        mimeType=None,
        progress_callback=None,
        pause_event: threading.Event = None,
        cancel_callback=None,
    ):
        mime_type = mimeType if mimeType else guess_type(file_path)[0]
        mime_type = mime_type if mime_type else "text/plain"
        controller = self._start_upload_session()
        filename = os.path.basename(file_path)
        total_size = os.path.getsize(file_path)
        local_md5 = self._compute_file_md5(file_path)
        body = {
            "name": filename,
            "description": "Uploaded using @UploadGdriveBot",
            "mimeType": mime_type,
            "parents": [self.__parent_id],
        }
        existing_state = self._load_upload_state(file_path, total_size, local_md5)
        initial_resume_progress = 0
        if existing_state:
            initial_resume_progress = int(existing_state.get("progress", 0))
            chunk_size_state = existing_state.get("chunk_size")
            if chunk_size_state:
                try:
                    controller._set_current(int(chunk_size_state))
                except Exception:
                    LOGGER.debug("Failed to apply saved chunk size for %s", file_path, exc_info=True)
        loop = asyncio.get_running_loop()

        async def notify(progress):
            if not progress_callback:
                return
            if inspect.iscoroutinefunction(progress_callback):
                await progress_callback(progress, total_size)
            else:
                progress_callback(progress, total_size)

        def dispatch(progress):
            if not progress_callback:
                return
            if inspect.iscoroutinefunction(progress_callback):
                asyncio.run_coroutine_threadsafe(progress_callback(progress, total_size), loop)
            else:
                loop.call_soon_threadsafe(progress_callback, progress, total_size)

        def make_request():
            state = self._load_upload_state(file_path, total_size, local_md5)
            progress = 0
            if state:
                progress = int(state.get("progress", 0))
            media_body = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                chunksize=controller.current_size,
                resumable=True,
            )
            request = self.__service.files().create(
                body=body.copy(),
                media_body=media_body,
                fields="id",
                supportsAllDrives=True,
            )
            if state:
                session_uri = state.get("session_uri")
                if session_uri:
                    request.resumable_uri = session_uri
            if progress:
                try:
                    stream = media_body.stream()
                    stream.seek(progress)
                except Exception:
                    LOGGER.debug("Failed to seek upload stream for %s", file_path, exc_info=True)
                try:
                    media_body._progress = progress
                except AttributeError:
                    setattr(media_body, "_progress", progress)
            return request, media_body, progress

        def perform():
            request, media_body, starting_progress = make_request()
            last_progress = starting_progress

            def handle_chunk(progress, req, media):
                nonlocal last_progress
                session_uri = getattr(req, "resumable_uri", None)
                if session_uri:
                    self._save_upload_state(
                        file_path,
                        session_uri=session_uri,
                        progress=progress,
                        chunk_size=getattr(media, "chunksize", controller.current_size),
                        range_start=last_progress,
                        total_size=total_size,
                        checksum=local_md5,
                    )
                last_progress = progress

            return self._perform_chunked_upload(
                request,
                controller,
                on_progress=dispatch,
                pause_event=pause_event,
                cancel_callback=cancel_callback,
                on_chunk_success=handle_chunk,
            )

        async def run_upload():
            try:
                return await loop.run_in_executor(None, lambda: self._call(perform))
            except Exception as exc:
                raise exc

        try:
            await notify(initial_resume_progress)
            uploaded_file = await run_upload()
            await notify(total_size)
            self._clear_upload_state(file_path)
            file_id = uploaded_file.get("id")
            checksum_error = self._verify_remote_checksum(file_id, local_md5, filename)
            if checksum_error:
                return checksum_error
            filesize = format_bytes(total_size)
            return Messages.UPLOADED_SUCCESSFULLY.format(
                filename,
                self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file_id),
                filesize,
            )
        except RetryError as err:
            LOGGER.info("Total Attempts: %s", err.last_attempt.attempt_number)
            error = err.last_attempt.exception()
            if isinstance(error, HttpError) and error.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(error.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if reason in {"userRateLimitExceeded", "dailyLimitExceeded"}:
                    return Messages.RATE_LIMIT_EXCEEDED_MESSAGE
                return f"**ERROR:** {reason}"
            return f"**ERROR:** ```{str(error).replace('>', '').replace('<', '')}```"
        except HttpError as err:
            if err.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(err.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if reason in {"userRateLimitExceeded", "dailyLimitExceeded"}:
                    return Messages.RATE_LIMIT_EXCEEDED_MESSAGE
                return f"**ERROR:** {reason}"
            return f"**ERROR:** ```{str(err).replace('>', '').replace('<', '')}```"
        except Exception as e:
            return f"**ERROR:** ```{e}```"
        finally:
            self._finish_upload_session()

    def checkFolderLink(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            raise IndexError
        try:
            file = self._call(
                lambda: self.__service.files()
                .get(supportsAllDrives=True, fileId=file_id, fields="mimeType")
                .execute()
            )
        except HttpError as err:
            if err.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(err.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if "notFound" in reason:
                    return False, Messages.FILE_NOT_FOUND_MESSAGE.format(file_id)
                return False, f"**ERROR:** ```{str(err).replace('>', '').replace('<', '')}```"
            raise
        if str(file.get("mimeType")) == self.__G_DRIVE_DIR_MIME_TYPE:
            return True, file_id
        return False, Messages.NOT_FOLDER_LINK

    def delete_file(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return Messages.INVALID_GDRIVE_URL
        try:
            self._call(
                lambda: self.__service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            )
            return Messages.DELETED_SUCCESSFULLY.format(file_id)
        except HttpError as err:
            if err.resp.get("content-type", "").startswith("application/json"):
                reason = json.loads(err.content).get("error", {}).get("errors", [{}])[0].get("reason")
                if "notFound" in reason:
                    return Messages.FILE_NOT_FOUND_MESSAGE.format(file_id)
                if "insufficientFilePermissions" in reason:
                    return Messages.INSUFFICIENT_PERMISSONS.format(file_id)
                return f"**ERROR:** ```{str(err).replace('>', '').replace('<', '')}```"
            raise

    def emptyTrash(self):
        try:
            self._call(lambda: self.__service.files().emptyTrash().execute())
            return Messages.EMPTY_TRASH
        except HttpError as err:
            return f"**ERROR:** ```{str(err).replace('>', '').replace('<', '')}```"

    def authorize(self, creds):
        return build("drive", "v3", credentials=creds, cache_discovery=False)
