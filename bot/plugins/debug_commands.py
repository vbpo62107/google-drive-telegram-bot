from pyrogram import Client, filters
from pyrogram.types import Message

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands


DOWNLOAD_ALIASES = set(BotCommands.Download)
LIST_ALIASES = set(BotCommands.ListDrive)
SEARCH_ALIASES = set(BotCommands.SearchDrive)


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(["download", "dl", "mirror", "listdrive", "searchdrive"])
    & filters.user(SUDO_USERS),
    group=1,
)
async def debug_command_router(client: Client, message: Message) -> None:
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
    except Exception as exc:
        LOGGER.exception("DEBUG router failed for command %s: %s", command, exc)
        await message.reply_text(f"⚠️ 命令执行出错：{exc}", quote=True)
