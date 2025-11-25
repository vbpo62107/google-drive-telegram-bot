import asyncio

from pyrogram import Client, filters

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters
from bot.plugins.utils import mark_command_handled
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
)


@Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.Delete) & CustomFilters.auth_users)
async def _delete(client, message):
    mark_command_handled(message)
    user = message.from_user
    if user is None or user.id not in SUDO_USERS:
        await message.reply_text("⚠️ 您没有权限使用此命令.", quote=True)
        return
    user_id = user.id
    if not (len(message.command) > 1 or message.reply_to_message):
        await message.reply_text(Messages.PROVIDE_GDRIVE_URL.format(BotCommands.Delete[0]), quote=True)
        return
    sent_message = await message.reply_text("🕵️**Checking Link...**", quote=True)
    if len(message.command) > 1:
        link = message.command[1]
    elif message.reply_to_message.entities and len(message.reply_to_message.entities) > 1 and message.reply_to_message.entities[1].url:
        link = message.reply_to_message.entities[1].url
    else:
        await sent_message.edit(Messages.PROVIDE_GDRIVE_URL.format(BotCommands.Delete[0]))
        return
    LOGGER.info("Delete:%s: %s", user_id, link)
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await sent_message.edit(drive_error_message(exc.code))
        return
    except Exception as exc:
        await sent_message.edit(f"**ERROR:** ```{exc}```")
        return
    result = await asyncio.to_thread(drive.delete_file, link)
    await sent_message.edit(result)


@Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.EmptyTrash) & CustomFilters.auth_users)
async def _emptyTrash(client, message):
    mark_command_handled(message)
    user = message.from_user
    if user is None or user.id not in SUDO_USERS:
        await message.reply_text("⚠️ 您没有权限使用此命令.", quote=True)
        return
    user_id = user.id
    LOGGER.info("EmptyTrash: %s", user_id)
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await message.reply_text(drive_error_message(exc.code), quote=True)
        return
    except Exception as exc:
        await message.reply_text(f"**ERROR:** ```{exc}```", quote=True)
        return
    msg = await asyncio.to_thread(drive.emptyTrash)
    await message.reply_text(msg, quote=True)
