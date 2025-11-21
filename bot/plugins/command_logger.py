from itertools import chain

from pyrogram import Client, filters

from bot import LOGGER
from bot.config import BotCommands

# 汇总需要记录的命令别名
COMMAND_ALIASES = list(
    chain(
        BotCommands.Clone,
        BotCommands.Delete,
        BotCommands.EmptyTrash,
        BotCommands.Download,
        BotCommands.YtDl,
        BotCommands.ListDrive,
        BotCommands.SearchDrive,
        BotCommands.SetFolder,
        BotCommands.Authorize,
        BotCommands.AuthMode,
        BotCommands.Revoke,
    )
)


@Client.on_message(filters.incoming & filters.command(COMMAND_ALIASES), group=0)
async def _command_logger(client, message):
    command = None
    if hasattr(message, "command") and message.command:
        command = (message.command[0] or "").lstrip("/").lower()
    LOGGER.info(
        "CMD hit: user=%s chat=%s command=%s text=%r",
        getattr(message.from_user, "id", None),
        getattr(message.chat, "id", None),
        command,
        message.text,
    )


@Client.on_message(filters.incoming, group=1)
async def _message_logger(client, message):
    LOGGER.info(
        "MSG hit: user=%s chat=%s is_private=%s text=%r",
        getattr(message.from_user, "id", None),
        getattr(message.chat, "id", None),
        getattr(message.chat, "type", None) == "private",
        message.text,
    )
