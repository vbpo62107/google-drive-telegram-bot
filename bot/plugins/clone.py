import asyncio
from pyrogram import Client, filters

from bot import SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters
from bot.modules.drive_helper import get_drive_instance


@Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.Clone) & CustomFilters.auth_users)
async def clone_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) <= 1 or not parts[1].strip():
        await client.send_message(message.chat.id, Messages.PROVIDE_GDRIVE_URL.format(BotCommands.Clone[0]))
        return
    link = parts[1].strip()
    try:
        drive = await get_drive_instance(str(message.from_user.id))
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")
        return
    status = await client.send_message(message.chat.id, Messages.CLONING.format(link), reply_to_message_id=message.id)
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, drive.clone, link)
    except Exception as exc:
        await client.edit_message_text(message.chat.id, status.id, f"❌ {exc}")
        return
    await client.edit_message_text(message.chat.id, status.id, result)
    return result
