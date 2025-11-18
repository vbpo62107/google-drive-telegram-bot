from pyrogram import Client, filters
from pyrogram.types import Message

from bot import LOGGER, SUDO_USERS


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(["download", "dl", "mirror", "listdrive", "searchdrive"])
    & filters.user(SUDO_USERS),
    group=1,
)
async def debug_command_logger(client: Client, message: Message) -> None:
    command = None
    if hasattr(message, "command") and message.command:
        command = message.command[0]
    LOGGER.info("DEBUG handler hit: user=%s command=%s text=%r", getattr(message.from_user, "id", None), command, message.text)
    await message.reply_text("🐛 调试：命令已收到，但主处理器可能未执行。", quote=True)
