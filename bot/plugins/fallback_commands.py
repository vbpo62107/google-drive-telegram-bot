import logging
from itertools import chain

from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper import gDriveDB

AUTH_REQUIRED = set(
    chain(
        BotCommands.Clone,
        BotCommands.Delete,
        BotCommands.EmptyTrash,
        BotCommands.SetFolder,
        BotCommands.Download,
        BotCommands.YtDl,
        BotCommands.Revoke,
        BotCommands.ListDrive,
        BotCommands.SearchDrive,
        BotCommands.Authorize,
        BotCommands.AuthMode,
        ["mirror", "addmonitor", "listmonitor", "togglemonitor", "delmonitor"],
    )
)

SUDO_REQUIRED = set(chain(AUTH_REQUIRED, ["log", "restart"]))
ALL_KNOWN_COMMANDS = set(chain(AUTH_REQUIRED, {"start", "help"}))


@Client.on_message(filters.private & filters.incoming & filters.regex(r"^/"), group=99)
async def _fallback_commands(client, message):
    """
    Fallback: if no handler responds, give a clear hint instead of silence.
    注意：`/ytdl` 与 `/download` 等高权限命令的特殊处理已明确取消，
    这里只提供统一的兜底提示，具体业务逻辑应由对应的插件处理。
    """
    raw = (message.text or "").split()[0]
    command = raw.split("@", 1)[0].lstrip("/").lower()
    if not command or command not in ALL_KNOWN_COMMANDS:
        return
    user_id = getattr(message.from_user, "id", 0) or 0

    # Permission checks
    if command in SUDO_REQUIRED and user_id not in SUDO_USERS:
        await message.reply_text(
            "⚠️ 您没有权限使用此命令。",
            quote=True,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return
    if command in AUTH_REQUIRED:
        try:
            if not gDriveDB.is_authorized(user_id):
                await message.reply_text(
                    Messages.NOT_AUTH,
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
                return
        except Exception as exc:
            LOGGER.error("Fallback auth check failed: user=%s err=%s", user_id, exc)
            await message.reply_text(
                Messages.DB_ERROR,
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            return

    # Generic fallback
    try:
        await message.reply_text(
            "⚠️ 命令已收到，但处理器未响应，请稍后重试或检查配置。",
            quote=True,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except Exception:
        logging.exception("Fallback send failed: user=%s command=%s", user_id, command)
        await message.reply_text(
            "⚠️ 命令已收到，但处理器未响应，请稍后重试或检查配置。",
            quote=True,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
