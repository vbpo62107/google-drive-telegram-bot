from itertools import chain

from pyrogram import Client, filters

from bot import LOGGER
from bot.config import BotCommands

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


def _normalize_command(message):
    if hasattr(message, "command") and message.command:
        return (message.command[0] or "").lstrip("/").lower()
    text = (message.text or "").strip()
    if text.startswith("/"):
        return text.split()[0].split("@")[0].lstrip("/").lower()
    return None


@Client.on_message(filters.incoming & filters.command(COMMAND_ALIASES), group=0)
async def _command_logger(client, message):
    command = _normalize_command(message)
    LOGGER.info(
        "Command hit user=%s chat=%s type=%s cmd=%s text=%r",
        getattr(message.from_user, "id", None),
        getattr(message.chat, "id", None),
        getattr(message.chat, "type", None),
        command,
        message.text,
    )


@Client.on_message(filters.incoming, group=1)
async def _message_logger(client, message):
    command = _normalize_command(message)
    LOGGER.info(
        "Message log user=%s chat=%s type=%s cmd=%s text=%r",
        getattr(message.from_user, "id", None),
        getattr(message.chat, "id", None),
        getattr(message.chat, "type", None),
        command,
        message.text,
    )
