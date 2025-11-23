import asyncio
import shutil
from os import execl
from sys import executable

from bot import DOWNLOAD_DIRECTORY, LOGGER, SUDO_USERS
from bot.helpers.utils import get_floodwait_seconds
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError


@Client.on_message(
    filters.private & filters.incoming & filters.command(["log"]) & filters.user(SUDO_USERS),
    group=2,
)
async def _send_log(client, message):
    with open("log.txt", "rb") as handle:
        try:
            await client.send_document(
                message.chat.id,
                document=handle,
                file_name=handle.name,
                reply_to_message_id=message.id,
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.info("Log file sent to %s", message.from_user.id)
        except FloodWait as exc:
            wait_seconds = get_floodwait_seconds(exc) or 1
            await asyncio.sleep(wait_seconds)
        except RPCError as exc:
            await message.reply_text(exc, quote=True, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(
    filters.private & filters.incoming & filters.command(["restart"]) & filters.user(SUDO_USERS),
    group=2,
)
async def _restart(client, message):
    shutil.rmtree(DOWNLOAD_DIRECTORY)
    LOGGER.info("Deleted DOWNLOAD_DIRECTORY successfully.")
    await message.reply_text("**♻️Restarted Successfully !**", quote=True, parse_mode=ParseMode.MARKDOWN)
    LOGGER.info("%s: Restarting...", message.from_user.id)
    execl(executable, executable, "-m", "bot")
