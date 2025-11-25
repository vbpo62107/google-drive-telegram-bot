from pyrogram import Client, filters
from pyrogram.types import Message

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands
from bot.helpers.utils import CustomFilters
from bot.plugins.utils import mark_command_handled


DOWNLOAD_ALIASES = set(BotCommands.Download)
LIST_ALIASES = set(BotCommands.ListDrive)
SEARCH_ALIASES = set(BotCommands.SearchDrive)
SETFOLDER_ALIASES = set(BotCommands.SetFolder)
MONITOR_ADD = {"addmonitor"}
MONITOR_LIST = {"listmonitor"}
MONITOR_TOGGLE = {"togglemonitor"}
MONITOR_DELETE = {"delmonitor"}


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(
        [
            # download / dl
            *BotCommands.Download,
            # mirror
            "mirror",
            # listdrive aliases
            *BotCommands.ListDrive,
            # searchdrive aliases
            *BotCommands.SearchDrive,
            # setfolder aliases
            *BotCommands.SetFolder,
            # monitor commands
            "addmonitor",
            "listmonitor",
            "togglemonitor",
            "delmonitor",
        ]
    )
    & filters.user(SUDO_USERS),
    group=1,
)
async def debug_command_router(client: Client, message: Message) -> None:
    mark_command_handled(message)
    command = None
    if hasattr(message, "command") and message.command:
        command = (message.command[0] or "").lstrip("/").lower()
    LOGGER.info(
        "DEBUG router hit: user=%s command=%s text=%r",
        getattr(message.from_user, "id", None),
        command,
        message.text,
    )
    try:
        if command in DOWNLOAD_ALIASES:
            from bot.modules.download_manager import download_handler

            await download_handler(client, message)
            return
        if command == "mirror":
            from bot.modules.mirror import mirror_handler

            await mirror_handler(client, message)
            return
        if command in LIST_ALIASES:
            from bot.modules.list_drive import list_drive_handler

            await list_drive_handler(client, message)
            return
        if command in SEARCH_ALIASES:
            from bot.modules.search_drive import search_drive_handler

            await search_drive_handler(client, message)
            return
        if command in SETFOLDER_ALIASES:
            from bot.plugins.set_parent import _set_parent

            await _set_parent(client, message)
            return
        if command in MONITOR_ADD:
            from bot.modules.auto_capture import add_monitor_handler

            await add_monitor_handler(client, message)
            return
        if command in MONITOR_LIST:
            from bot.modules.auto_capture import list_monitor_handler

            await list_monitor_handler(client, message)
            return
        if command in MONITOR_TOGGLE:
            from bot.modules.auto_capture import toggle_monitor_handler

            await toggle_monitor_handler(client, message)
            return
        if command in MONITOR_DELETE:
            from bot.modules.auto_capture import delete_monitor_handler

            await delete_monitor_handler(client, message)
            return
    except Exception as exc:
        LOGGER.exception("DEBUG router failed for command %s: %s", command, exc)
        await message.reply_text(f"⚠️ 命令执行出错：{exc}", quote=True)


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(BotCommands.YtDl)
    & CustomFilters.auth_users,
    group=1,
)
async def ytdl_command_router(client: Client, message: Message) -> None:
    mark_command_handled(message)
    LOGGER.info(
        "YTDL router hit: user=%s text=%r",
        getattr(message.from_user, "id", None),
        message.text,
    )
    from bot.modules.download_manager import ytdl_handler

    await ytdl_handler(client, message)
