from itertools import chain

from pyrogram import Client, filters

from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters
from bot.plugins.utils import mark_command_handled


AUTH_REQUIRED_COMMANDS = list(
    chain(
        BotCommands.Clone,
        BotCommands.Delete,
        BotCommands.EmptyTrash,
        BotCommands.SetFolder,
        BotCommands.Download,
        BotCommands.YtDl,
        BotCommands.Revoke,
    )
)

PRIVATE_ONLY_COMMANDS = list(
    chain(
        AUTH_REQUIRED_COMMANDS,
        BotCommands.ListDrive,
        BotCommands.SearchDrive,
        BotCommands.Authorize,
        BotCommands.AuthMode,
        [
            "mirror",
            "addmonitor",
            "listmonitor",
            "togglemonitor",
            "delmonitor",
            "log",
            "restart",
            "start",
            "help",
        ],
    )
)


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(AUTH_REQUIRED_COMMANDS)
    & ~CustomFilters.auth_users
)
async def _auth_required_feedback(client: Client, message):
    mark_command_handled(message)
    await message.reply_text(Messages.NOT_AUTH, quote=True)


@Client.on_message(
    filters.group
    & filters.command(PRIVATE_ONLY_COMMANDS)
)
async def _group_redirect(client: Client, message):
    mark_command_handled(message)
    await message.reply_text(Messages.GROUP_USE_PRIVATE, quote=True)


@Client.on_message(filters.group & filters.regex(r"^/"), group=20)
async def _group_any_command(client: Client, message):
    """
    兜底：群里任何斜杠命令都提示去私聊，避免过滤器未匹配时出现“无响应”。
    """
    try:
        await message.reply_text(Messages.GROUP_USE_PRIVATE, quote=True)
    except Exception:
        pass
