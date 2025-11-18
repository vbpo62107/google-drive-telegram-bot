import atexit
import importlib
import logging
import os
import pkgutil

from pyrogram import Client

from bot import (
  APP_ID,
  API_HASH,
  BOT_TOKEN,
  DOWNLOAD_DIRECTORY
  )
from bot.modules.drive_helper import cleanup_drive_instances

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

atexit.register(cleanup_drive_instances)


def load_module_plugins() -> None:
    try:
        import bot.modules as modules_pkg
    except Exception:
        LOGGER.exception("无法加载模块包 bot.modules")
        return

    for module_info in pkgutil.walk_packages(modules_pkg.__path__, modules_pkg.__name__ + "."):
        if module_info.ispkg or module_info.name.split(".")[-1].startswith("_"):
            continue
        try:
            importlib.import_module(module_info.name)
        except Exception:
            LOGGER.exception("无法导入模块 %s", module_info.name)


if __name__ == "__main__":
    if not os.path.isdir(DOWNLOAD_DIRECTORY):
        os.makedirs(DOWNLOAD_DIRECTORY)
    load_module_plugins()
    plugins = dict(
        root="bot/plugins"
    )
    app = Client(
        "G-DriveBot",
        bot_token=BOT_TOKEN,
        api_id=APP_ID,
        api_hash=API_HASH,
        plugins=plugins,
        workdir=DOWNLOAD_DIRECTORY
    )
    LOGGER.info('Starting Bot !')
    app.run()
    LOGGER.info('Bot Stopped !')
