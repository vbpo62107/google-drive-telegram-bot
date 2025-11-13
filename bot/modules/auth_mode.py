from pyrogram import Client, filters

from bot import SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
from bot.modules.drive_helper import invalidate_drive_instance


@Client.on_message(filters.private & filters.command(BotCommands.AuthMode))
async def auth_mode_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    if len(message.command) <= 1:
        await client.send_message(message.chat.id, Messages.AUTHMODE_USAGE, quote=True)
        return
    option = message.command[1].strip().lower()
    user_id = message.from_user.id
    if option == "service":
        if not credential_manager.service_account_available():
            await client.send_message(message.chat.id, Messages.AUTHMODE_SERVICE_UNAVAILABLE, quote=True)
            return
        fingerprint = credential_manager.service_account_fingerprint()
        payload = {"mode": "service_account"}
        gDriveDB.save_credentials(
            user_id,
            mode="service_account",
            payload=payload,
            fingerprint=fingerprint,
            device=f"service:{user_id}",
        )
        gDriveDB.reset_failures(user_id)
        invalidate_drive_instance(user_id)
        await client.send_message(message.chat.id, Messages.AUTHMODE_SERVICE_ENABLED, quote=True)
        return
    if option == "oauth":
        gDriveDB._clear(user_id)
        gDriveDB.reset_failures(user_id)
        invalidate_drive_instance(user_id)
        await client.send_message(message.chat.id, Messages.AUTHMODE_OAUTH_ENABLED, quote=True)
        return
    await client.send_message(message.chat.id, Messages.AUTHMODE_USAGE, quote=True)
