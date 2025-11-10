from dataclasses import dataclass
from threading import RLock
from typing import Optional

from cachetools import TTLCache

from bot.helpers.gdrive_utils.gDrive import GoogleDrive
from bot.helpers.sql_helper import gDriveDB, idsDB

_cache: TTLCache[str, "_CacheEntry"] = TTLCache(maxsize=64, ttl=1800)
_cache_lock = RLock()


@dataclass
class _CacheEntry:
    drive: GoogleDrive
    parent_id: Optional[str]
    credential_fingerprint: Optional[str]


def _normalize_user_id(user_id: str):
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return user_id


def _fingerprint_credentials(user_id) -> Optional[str]:
    creds = gDriveDB.search(user_id)
    if creds is None:
        return None
    to_json = getattr(creds, "to_json", None)
    if callable(to_json):
        try:
            return to_json()
        except Exception:
            pass
    attributes = []
    for attr in ("refresh_token", "client_id", "client_secret", "token", "access_token"):
        attributes.append(str(getattr(creds, attr, None)))
    return "|".join(attributes)


async def get_drive_instance(user_id: str) -> GoogleDrive:
    normalized_id = _normalize_user_id(user_id)
    parent_id = idsDB.search_parent(normalized_id)
    credential_fingerprint = _fingerprint_credentials(normalized_id)
    key = str(normalized_id)
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry.parent_id == parent_id and entry.credential_fingerprint == credential_fingerprint:
            return entry.drive
    drive = GoogleDrive(normalized_id)
    cache_entry = _CacheEntry(drive=drive, parent_id=parent_id, credential_fingerprint=credential_fingerprint)
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
