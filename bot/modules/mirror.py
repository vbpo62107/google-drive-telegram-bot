import asyncio
import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import DEFAULT_AUTH_MODE, LOGGER, SUDO_USERS
from bot.config import Messages
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.sql_helper.mirror_tasks import MirrorTask, MirrorTaskStatus
from bot.helpers.sql_helper import get_session
from bot.helpers.utils import extract_filename_from_url
from bot.modules.task_manager import task_manager


async def _update_stage(task_id: int, stage: str) -> None:
    def op():
        with get_session() as session:
            record = session.query(MirrorTask).get(task_id)
            if record:
                record.stage = stage
                if record.status != MirrorTaskStatus.PAUSED.value:
                    record.status = MirrorTaskStatus.PENDING.value
                session.add(record)
                session.commit()

    await asyncio.to_thread(op)


def _initial_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸️ 暂停", callback_data=f"mirror:{task_id}:pause"),
                InlineKeyboardButton("🛑 取消", callback_data=f"mirror:{task_id}:cancel"),
            ]
        ]
    )


@Client.on_message(filters.command("mirror") & filters.private)
async def mirror_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, Messages.MIRROR_NO_PERMISSION)
        return
    if not message.text or len(message.text.split(maxsplit=1)) < 2:
        await client.send_message(message.chat.id, Messages.MIRROR_PROVIDE_URL)
        return
    url = message.text.split(maxsplit=1)[1].strip()
    if not re.match(r"^https?://", url, re.I):
        await client.send_message(message.chat.id, Messages.MIRROR_UNSUPPORTED_PROTOCOL)
        return
    try:
        authorized = gDriveDB.is_authorized(message.from_user.id)
        if not authorized and DEFAULT_AUTH_MODE == "service_account":
            authorized = credential_manager.service_account_available()
    except Exception as exc:
        LOGGER.error("Mirror auth check failed for user %s: %s", message.from_user.id, exc)
        await client.send_message(message.chat.id, Messages.DB_ERROR)
        return
    if not authorized:
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    filename = extract_filename_from_url(url, "downloaded_file")
    try:
        runner = await task_manager.submit(client, message.from_user.id, message.chat.id, url, filename)
        sent = await client.send_message(
            message.chat.id,
            f"📥 任务已创建\nID: {runner.id}\n文件: `{filename}`\n状态: 排队中",
            reply_markup=_initial_keyboard(runner.id),
        )
        await task_manager.update_message_id(runner.id, sent.id)
        await _update_stage(runner.id, "排队中")
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")


@Client.on_callback_query(filters.regex(r"^mirror:(\d+):(pause|resume|cancel)$"))
async def mirror_callback_handler(client, query):
    if query.from_user is None or query.from_user.id not in SUDO_USERS:
        await query.answer("⚠️ 无权操作", show_alert=True)
        return
    data = query.data.split(":")
    task_id = int(data[1])
    action = data[2]
    try:
        if action == "pause":
            changed = await task_manager.pause(client, task_id)
            await query.answer("⏸️ 已暂停" if changed else "⚠️ 无法暂停", show_alert=True)
        elif action == "resume":
            changed = await task_manager.resume(client, task_id)
            await query.answer("▶️ 已继续" if changed else "⚠️ 无法继续", show_alert=True)
        elif action == "cancel":
            changed = await task_manager.cancel(client, task_id)
            await query.answer("🛑 已取消" if changed else "⚠️ 无法取消", show_alert=True)
    except Exception as exc:
        await query.answer(f"⚠️ {exc}", show_alert=True)
