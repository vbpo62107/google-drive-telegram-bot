from threading import RLock
from cachetools import TTLCache

from bot.helpers.gdrive_utils.gDrive import GoogleDrive

_cache = TTLCache(maxsize=64, ttl=1800)
_cache_lock = RLock()


def _normalize_user_id(user_id: str):
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return user_id


async def get_drive_instance(user_id: str) -> GoogleDrive:
    key = str(user_id)
    with _cache_lock:
        instance = _cache.get(key)
        if instance is None:
            instance = GoogleDrive(_normalize_user_id(user_id))
            _cache[key] = instance
    return instance


def cleanup_drive_instances() -> None:
    with _cache_lock:
        instances = list(_cache.values())
        _cache.clear()
    for instance in instances:
        close = getattr(instance, "close", None)
        if callable(close):
            close()
