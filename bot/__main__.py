import atexit
import logging
import os
from importlib import import_module
from pathlib import Path
from typing import List

from pyrogram import Client
from pyrogram.enums import ParseMode

from bot import APP_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIRECTORY
from bot.modules.drive_helper import cleanup_drive_instances

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8-sig"),
        logging.StreamHandler(),
    ],
    force=True,
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

atexit.register(cleanup_drive_instances)


MODULE_NAMES: List[str] = [
    "auth_mode",
    "auto_capture",
    "download_manager",
    "list_drive",
    "mirror",
    "search_drive",
]


def _import_modules() -> None:
    """
    Ensure all bot.modules.* handlers are imported so their
    @Client.on_message decorators are registered even when the
    plugin loader is not used.
    """
    for name in MODULE_NAMES:
        import_path = f"bot.modules.{name}"
        try:
            import_module(import_path)
        except Exception:  # pragma: no cover - fail fast on import errors
            LOGGER.exception("Failed to import module %s", import_path)
            raise


def _import_plugins() -> None:
    """
    Import all bot.plugins.* modules so their handlers are registered
    even if Pyrogram's plugin loader fails to locate the root path.
    """
    base_path = Path(__file__).resolve().parent / "plugins"
    if not base_path.is_dir():
        LOGGER.warning("Plugin directory not found: %s", base_path)
        return
    for path in base_path.glob("*.py"):
        if path.stem.startswith("_") or path.stem == "modules_loader":
            continue
        import_path = f"bot.plugins.{path.stem}"
        try:
            import_module(import_path)
            if import_path == "bot.plugins.help":
                LOGGER.info("Help plugin imported successfully: %s", import_path)
        except Exception:  # pragma: no cover - fail fast on import errors
            LOGGER.exception("Failed to import plugin %s", import_path)
            raise


if __name__ == "__main__":
    if not os.path.isdir(DOWNLOAD_DIRECTORY):
        os.makedirs(DOWNLOAD_DIRECTORY)

    # 使用包路径作为插件根，避免传入文件系统路径导致导入错误
    plugin_root = "bot.plugins"
    LOGGER.info("Plugin root: %s", plugin_root)

    # Import core modules so that all command handlers inside
    # bot.modules are registered, regardless of plugin settings.
    _import_modules()
    # Import plugin modules explicitly to avoid silent plugin loader failures.
    _import_plugins()

    plugins = {"root": plugin_root}
    app = Client(
        "G-DriveBot",
        bot_token=BOT_TOKEN,
        api_id=APP_ID,
        api_hash=API_HASH,
        workdir=DOWNLOAD_DIRECTORY,
        plugins=plugins,
        parse_mode=ParseMode.MARKDOWN,
    )
    LOGGER.info("Starting bot...")
    app.run()
    LOGGER.info("Bot stopped.")
