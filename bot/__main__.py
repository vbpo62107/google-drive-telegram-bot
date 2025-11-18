import atexit
import logging
import os
from importlib import import_module
from typing import List

from pyrogram import Client

from bot import APP_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIRECTORY
from bot.modules.drive_helper import cleanup_drive_instances

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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


if __name__ == "__main__":
    if not os.path.isdir(DOWNLOAD_DIRECTORY):
        os.makedirs(DOWNLOAD_DIRECTORY)

    # Import core modules so that all command handlers inside
    # bot.modules are registered, regardless of plugin settings.
    _import_modules()

    plugins = {"root": "bot/plugins"}
    app = Client(
        "G-DriveBot",
        bot_token=BOT_TOKEN,
        api_id=APP_ID,
        api_hash=API_HASH,
        plugins=plugins,
        workdir=DOWNLOAD_DIRECTORY,
    )
    LOGGER.info("Starting Bot !")
    app.run()
    LOGGER.info("Bot Stopped !")
