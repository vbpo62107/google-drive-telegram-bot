from itertools import chain

from pyrogram import Client, filters

from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters


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


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(AUTH_REQUIRED_COMMANDS)
    & ~CustomFilters.auth_users
)
async def _auth_required_feedback(client: Client, message):
    await message.reply_text(Messages.NOT_AUTH, quote=True)


@Client.on_message(
    filters.group
    & filters.command(AUTH_REQUIRED_COMMANDS)
)
async def _group_redirect(client: Client, message):
    await message.reply_text("⚠️ 请在与机器人私聊中使用此命令。", quote=True)
