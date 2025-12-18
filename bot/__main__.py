import atexit
import logging
import os
from importlib import import_module
from pathlib import Path
from typing import List

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.handlers import CallbackQueryHandler

from bot import APP_ID, API_HASH, BOT_TOKEN, DOWNLOAD_DIRECTORY
from bot.helpers.utils import CustomFilters
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
    "oneonefive_manager",
    "search_drive",
]


def _import_modules() -> None:
    """
    Ensure all bot.modules.* handlers are imported so their
    @Client.on_message decorators are registered even when the
    plugin loader is not used.
    """
    LOGGER.info("Importing %d modules", len(MODULE_NAMES))
    for name in MODULE_NAMES:
        import_path = f"bot.modules.{name}"
        LOGGER.info("Importing module %s", import_path)
        try:
            import_module(import_path)
            LOGGER.info("Successfully imported module %s", import_path)
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
    # 手动注册所有命令处理器（确保可靠性）
    from pyrogram.handlers import MessageHandler
    from bot.modules.download_manager import ytdl_handler, download_handler
    from bot.modules.mirror import mirror_handler
    from bot.modules.auto_capture import (
        add_monitor_handler,
        list_monitor_handler,
        toggle_monitor_handler,
        delete_monitor_handler,
    )
    from bot.modules.auth_mode import auth_mode_handler
    from bot.modules.search_drive import search_drive_handler
    from bot.modules.list_drive import list_drive_handler
    from bot.modules.oneonefive_manager import oneonefive_auth_handler, oneonefive_upload_handler
    # 添加 plugins 中的处理器
    from bot.plugins.clone import clone_handler
    from bot.plugins.delete import delete_handler, emptytrash_handler
    from bot.plugins.set_parent import setfolder_handler
    from bot.plugins.authorize import auth_handler, revoke_handler

    LOGGER.info("="*60)
    LOGGER.info("Registering all command handlers manually...")

    # Download & YtDl
    app.add_handler(
        MessageHandler(download_handler, filters.private & filters.command(["download", "dl"])),
        group=-1
    )
    LOGGER.info("✅ download_handler registered")

    app.add_handler(
        MessageHandler(ytdl_handler, filters.private & filters.command(["ytdl"])),
        group=-1
    )
    LOGGER.info("✅ ytdl_handler registered")

    # Mirror
    app.add_handler(
        MessageHandler(mirror_handler, filters.private & filters.command(["mirror"])),
        group=-1
    )
    LOGGER.info("✅ mirror_handler registered")

    # Auth Mode
    app.add_handler(
        MessageHandler(auth_mode_handler, filters.private & filters.command(["authmode"])),
        group=-1
    )
    LOGGER.info("✅ auth_mode_handler registered")

    # Search Drive
    app.add_handler(
        MessageHandler(search_drive_handler, filters.private & filters.command(["searchdrive", "sdrive"])),
        group=-1
    )
    LOGGER.info("✅ search_drive_handler registered")

    # List Drive
    app.add_handler(
        MessageHandler(list_drive_handler, filters.private & filters.command(["listdrive", "lsdrive", "listdriv"])),
        group=-1
    )
    LOGGER.info("✅ list_drive_handler registered")

    # 115 授权与上传
    app.add_handler(
        MessageHandler(
            oneonefive_auth_handler,
            filters.private & filters.incoming & filters.command(["115auth", "115login"]) & CustomFilters.auth_users,
        ),
        group=-1,
    )
    LOGGER.info("✅ oneonefive_auth_handler registered")

    app.add_handler(
        MessageHandler(
            oneonefive_upload_handler,
            filters.private & filters.incoming & filters.command(["115upload"]) & CustomFilters.auth_users,
        ),
        group=-1,
    )
    LOGGER.info("✅ oneonefive_upload_handler registered")

    # Auto Capture Monitors
    app.add_handler(
        MessageHandler(add_monitor_handler, filters.private & filters.command(["addmonitor"])),
        group=-1
    )
    LOGGER.info("✅ add_monitor_handler registered")

    app.add_handler(
        MessageHandler(list_monitor_handler, filters.private & filters.command(["listmonitor"])),
        group=-1
    )
    LOGGER.info("✅ list_monitor_handler registered")

    app.add_handler(
        MessageHandler(toggle_monitor_handler, filters.private & filters.command(["togglemonitor"])),
        group=-1
    )
    LOGGER.info("✅ toggle_monitor_handler registered")

    app.add_handler(
        MessageHandler(delete_monitor_handler, filters.private & filters.command(["delmonitor"])),
        group=-1
    )
    LOGGER.info("✅ delete_monitor_handler registered")

    # Auto Capture Listener (monitor channel messages)
    from bot.modules.auto_capture import auto_capture_listener

    app.add_handler(
        MessageHandler(auto_capture_listener, filters.channel),
        group=1  # 低优先级，不与命令冲突
    )
    LOGGER.info("✅ auto_capture_listener registered")

    # Plugins handlers - Clone/Copy
    app.add_handler(
        MessageHandler(
            clone_handler,
            filters.private & filters.command(["clone", "copy"]),
        ),
        group=-1
    )
    LOGGER.info("✅ clone_handler registered")

    # Plugins handlers - Delete
    app.add_handler(
        MessageHandler(
            delete_handler,
            filters.private & filters.command(["delete", "del"]),
        ),
        group=-1
    )
    LOGGER.info("✅ delete_handler registered")

    # Plugins handlers - EmptyTrash
    app.add_handler(
        MessageHandler(
            emptytrash_handler,
            filters.private & filters.command(["emptytrash", "emptyTrash"]),
        ),
        group=-1
    )
    LOGGER.info("✅ emptytrash_handler registered")

    # Plugins handlers - SetFolder
    app.add_handler(
        MessageHandler(
            setfolder_handler,
            filters.private & filters.command(["setfolder", "setfl"]),
        ),
        group=-1
    )
    LOGGER.info("✅ setfolder_handler registered")

    # Plugins handlers - Authorize
    app.add_handler(
        MessageHandler(
            auth_handler,
            filters.private & filters.command(["auth", "authorize"]),
        ),
        group=-1
    )
    LOGGER.info("✅ auth_handler registered")

    # Plugins handlers - Revoke
    app.add_handler(
        MessageHandler(
            revoke_handler,
            filters.private & filters.command(["revoke"]),
        ),
        group=-1
    )
    LOGGER.info("✅ revoke_handler registered")

    LOGGER.info("All command handlers registered successfully")
    LOGGER.info("="*60)
    # 临时调试
    @app.on_message()
    async def debug_catch_all(client, message):
        import logging

        logging.warning(
            "CATCH_ALL: Received message from chat_id=%s, type=%s",
            message.chat.id if message.chat else None,
            message.chat.type if message.chat else None,
        )

    LOGGER.info("Debug catch-all handler registered")

    # 手动注册 ytdl 回调处理器
    from bot.modules.download_manager import handle_ytdl_quality_selection

    app.add_handler(
        CallbackQueryHandler(
            handle_ytdl_quality_selection,
            filters.regex(r"^ytdl_select_")
        ),
        group=0
    )
    LOGGER.info("✅ ytdl_quality_selection handler manually registered via add_handler")

    # 临时调试回调
    @app.on_callback_query(group=-999)
    async def debug_callback_catch_all(client, callback_query):
        import logging

        logging.warning(
            "🔥🔥🔥 CALLBACK_CATCH_ALL: Received callback_data=%s from user=%s",
            callback_query.data,
            callback_query.from_user.id,
        )

    LOGGER.info("Starting bot...")
    app.run()
    LOGGER.info("Bot stopped.")
