import math
import os
import re
from urllib.parse import parse_qs, unquote, urlparse

from pyrogram import filters
from pyrogram.errors import FloodWait

from bot import DEFAULT_AUTH_MODE, LOGGER, SUDO_USERS
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB


def _is_authorized_user(_, __, message) -> bool:
    user = getattr(message, "from_user", None)
    user_id = getattr(user, "id", None)
    if user_id is None:
        return False
    # SUDO 用户始终允许通过高权限过滤器，具体权限和授权状态在各自命令内再做细粒度检查。
    if user_id in SUDO_USERS:
        return True
    try:
        if gDriveDB.is_authorized(user_id):
            return True
    except Exception as exc:
        LOGGER.error("Authorization lookup failed for user %s: %s", user_id, exc)
    if DEFAULT_AUTH_MODE == "service_account" and credential_manager.service_account_available():
        return True
    return False


class CustomFilters:
    auth_users = filters.create(_is_authorized_user)


def get_floodwait_seconds(exc: FloodWait) -> int:
    value = getattr(exc, "value", None)
    if value is None:
        value = getattr(exc, "x", 0)
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def format_bytes(size: int) -> str:
    if size is None:
        return ""
    size = float(size)
    if size <= 0:
        return "0 B"
    power = min(int(math.log(size, 1024)), 5)
    normalized = size / math.pow(1024, power)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    return f"{normalized:.2f} {units[power]}"


def render_progress_bar(current: int, total: int, width: int = 14) -> str:
    if total and total > 0:
        filled = min(width, int(width * (current / total)))
    else:
        filled = 0
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def format_seconds(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_elapsed_eta(elapsed: float, current: int, total: int) -> tuple[str, str]:
    elapsed_text = format_seconds(elapsed)
    if not total or total <= 0 or not current or elapsed <= 0:
        return elapsed_text, "--:--"
    remaining = max(total - current, 0)
    speed = current / elapsed if elapsed else 0
    if speed <= 0:
        return elapsed_text, "--:--"
    eta = remaining / speed
    return elapsed_text, format_seconds(eta)


def format_speed(speed: float) -> str:
    if speed <= 0:
        return "0 B/s"
    return f"{format_bytes(speed)}/s"


def extract_filename_from_url(url: str, default: str = "file") -> str:
    if not url:
        return default
    parsed = urlparse(url)
    candidates = []
    if parsed.path:
        candidates.append(os.path.basename(parsed.path))
    query = parse_qs(parsed.query)
    for key in ("filename", "file", "name"):
        if key in query and query[key]:
            candidates.append(query[key][-1])
    for candidate in candidates:
        decoded = unquote(candidate).strip()
        if decoded and not decoded.endswith('/'):
            sanitized = re.sub(r"[\n\r]", "", decoded)
            return sanitized
    return default


def humanbytes(size: int) -> str:
    if not size:
        return ""
    return format_bytes(size)
