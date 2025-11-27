import asyncio

from pyrogram import Client, filters

from bot import LOGGER
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper import idsDB
from bot.helpers.utils import CustomFilters
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
    invalidate_drive_instance,
)


# @Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.SetFolder) & CustomFilters.auth_users)
async def _set_parent(client, message):
    user_id = message.from_user.id
    if len(message.command) <= 1:
        await message.reply_text(
            Messages.CURRENT_PARENT.format(idsDB.search_parent(user_id), BotCommands.SetFolder[0]),
            quote=True,
        )
        return
    link = message.command[1]
    if "clear" in link:
        idsDB._clear(user_id)
        invalidate_drive_instance(user_id)
        await message.reply_text(Messages.PARENT_CLEAR_SUCCESS, quote=True)
        return
    sent_message = await message.reply_text("🕵️**Checking Link...**", quote=True)
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await sent_message.edit(drive_error_message(exc.code))
        return
    except Exception as exc:
        await sent_message.edit(f"**ERROR:** ```{exc}```")
        return
    try:
        result, file_id = await asyncio.to_thread(drive.checkFolderLink, link)
        if result:
            idsDB._set(user_id, file_id)
            LOGGER.info("SetParent:%s: %s", user_id, file_id)
            invalidate_drive_instance(user_id)
            await sent_message.edit(Messages.PARENT_SET_SUCCESS.format(file_id, BotCommands.SetFolder[0]))
        else:
            await sent_message.edit(file_id)
    except IndexError:
        await sent_message.edit(Messages.INVALID_GDRIVE_URL)


setfolder_handler = _set_parent
