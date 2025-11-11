from dataclasses import dataclass
from threading import RLock
from typing import Optional

from cachetools import TTLCache

from bot import DEFAULT_AUTH_MODE, LOGGER
from bot.config import Messages
from bot.helpers.gdrive_utils.gDrive import GoogleDrive
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB, idsDB

_cache: TTLCache[str, "_CacheEntry"] = TTLCache(maxsize=64, ttl=1800)
_cache_lock = RLock()


@dataclass
class _CacheEntry:
    drive: GoogleDrive
    parent_id: Optional[str]
    credential_fingerprint: Optional[str]
    mode: str


class DriveAccessError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def drive_error_message(code: str) -> str:
    if code == "missing_credentials":
        return Messages.NOT_AUTH
    if code == "circuit_open":
        return Messages.DRIVE_CIRCUIT_OPEN
    if code == "invalid_credentials":
        return Messages.INVALID_CREDENTIALS
    return Messages.WENT_WRONG


def _normalize_user_id(user_id: str):
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return user_id
async def get_drive_instance(user_id: str) -> GoogleDrive:
    normalized_id = _normalize_user_id(user_id)
    record = gDriveDB.search(normalized_id)
    if record is None and DEFAULT_AUTH_MODE == "service_account" and credential_manager.service_account_available():
        fingerprint = credential_manager.service_account_fingerprint()
        payload = {"mode": "service_account"}
        record = gDriveDB.save_credentials(
            normalized_id,
            mode="service_account",
            payload=payload,
            fingerprint=fingerprint,
            device=f"service:{normalized_id}",
        )
    if record is None:
        LOGGER.error("Missing credentials for user %s", normalized_id)
        raise DriveAccessError("missing_credentials")
    if gDriveDB.is_circuit_open(normalized_id):
        LOGGER.warning("Circuit breaker active for user %s", normalized_id)
        raise DriveAccessError("circuit_open")
    fingerprint = credential_manager.ensure_fingerprint(normalized_id, record)
    try:
        credentials = credential_manager.build_credentials(normalized_id, record)
    except Exception as exc:
        LOGGER.error("Failed to build credentials for user %s: %s", normalized_id, exc)
        raise DriveAccessError("invalid_credentials") from exc
    if credentials is None:
        LOGGER.error("Invalid credentials for user %s", normalized_id)
        raise DriveAccessError("invalid_credentials")
    parent_id = idsDB.search_parent(normalized_id)
    key = str(normalized_id)
    with _cache_lock:
        entry = _cache.get(key)
        if (
            entry
            and entry.parent_id == parent_id
            and entry.credential_fingerprint == fingerprint
            and entry.mode == record.mode
        ):
            return entry.drive
    drive = GoogleDrive(
        user_id=normalized_id,
        credentials=credentials,
        parent_id=parent_id,
        mode=record.mode,
        fingerprint=fingerprint,
    )
    cache_entry = _CacheEntry(
        drive=drive,
        parent_id=parent_id,
        credential_fingerprint=fingerprint,
        mode=record.mode,
    )
    with _cache_lock:
        _cache[key] = cache_entry
    return drive


def invalidate_drive_instance(user_id: str) -> None:
    key = str(_normalize_user_id(user_id))
    with _cache_lock:
        entry = _cache.pop(key, None)
    if entry is None:
        return
    close = getattr(entry.drive, "close", None)
    if callable(close):
        close()


def cleanup_drive_instances() -> None:
    with _cache_lock:
        entries = list(_cache.values())
        _cache.clear()
    for entry in entries:
        close = getattr(entry.drive, "close", None)
        if callable(close):
            close()
