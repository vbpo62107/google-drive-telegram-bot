import asyncio
import re
import time
from typing import List, Tuple

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import LOGGER, SUDO_USERS
from bot.helpers.sql_helper import get_session
from bot.helpers.sql_helper.keyword_monitors import (
    create_monitor,
    delete_monitor,
    get_enabled_monitors_by_channel,
    list_monitors,
    toggle_monitor,
)
from bot.helpers.sql_helper.mirror_tasks import MirrorTask, MirrorTaskStatus
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import extract_filename_from_url
from bot.modules.task_manager import task_manager


async def _resolve_owner() -> int:
    for user_id in SUDO_USERS:
        if gDriveDB.is_authorized(user_id):
            return user_id
    return 0


def _initial_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸️ 暂停", callback_data=f"mirror:{task_id}:pause"),
                InlineKeyboardButton("🛑 取消", callback_data=f"mirror:{task_id}:cancel"),
            ]
        ]
    )


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


def _format_monitor_line(record: dict) -> str:
    status = "启用" if record["enabled"] else "停用"
    keywords = ", ".join(record["keywords"]) if record["keywords"] else "-"
    return f"#{record['id']} 频道: {record['channel_id']} 状态: {status} 关键词: {keywords}"


def _parse_keywords(text: str) -> List[str]:
    parts = re.split(r"[,|]", text)
    keywords = []
    seen = set()
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(cleaned)
    return keywords


def _match_monitors(monitors: List[dict], content: str) -> Tuple[List[dict], List[str]]:
    matched = []
    keywords = set()
    lower = content.lower()
    for record in monitors:
        local_hits = []
        for keyword in record["keywords"]:
            if keyword.lower() in lower:
                local_hits.append(keyword)
        if local_hits:
            matched.append(record)
            keywords.update(local_hits)
    return matched, sorted(keywords)


def _extract_links(content: str) -> List[str]:
    return re.findall(r"https?://\S+", content, flags=re.I)


def _extract_media(message) -> str:
    media = None
    file_name = ""
    for attr in ("document", "video", "audio", "animation"):
        media = getattr(message, attr, None)
        if media:
            file_name = getattr(media, "file_name", "") or f"media_{message.chat.id}_{message.id}"
            break
    if not media and getattr(message, "photo", None):
        media = message.photo
        file_name = f"photo_{message.chat.id}_{message.id}.jpg"
    if not media and getattr(message, "voice", None):
        media = message.voice
        file_name = getattr(media, "file_name", "") or f"voice_{message.chat.id}_{message.id}.ogg"
    if not media:
        return ""
    return file_name


async def _notify_missing_credentials(client: Client, message, keywords: List[str]) -> None:
    channel_title = message.chat.title or str(message.chat.id)
    text = f"⚠️ 自动监听触发但缺少有效凭据\n频道: {channel_title} ({message.chat.id})\n关键词: {', '.join(keywords) if keywords else '-'}\n消息ID: {message.id}"
    for admin_id in SUDO_USERS:
        try:
            await client.send_message(admin_id, text)
        except Exception:
            continue


async def _notify_admins(client: Client, owner_id: int, task_id: int, message, keywords: List[str], file_name: str, source: str) -> None:
    channel_title = message.chat.title or str(message.chat.id)
    link = message.link or f"tg://{message.chat.id}/{message.id}"
    text = f"📢 频道触发监控\n频道: {channel_title} ({message.chat.id})\n关键词: {', '.join(keywords) if keywords else '-'}\n任务ID: {task_id}\n文件: `{file_name}`\n来源: {link}\n分配: {owner_id}\n源指纹: {source}"
    for admin_id in SUDO_USERS:
        if admin_id == owner_id:
            continue
        try:
            await client.send_message(admin_id, text)
        except Exception:
            continue


def _build_source(message) -> Tuple[str, str]:
    media_name = _extract_media(message)
    content = " ".join(part for part in [message.text, message.caption] if part)
    if media_name:
        return f"tg://{message.chat.id}/{message.id}", media_name
    links = _extract_links(content)
    if links:
        default = f"auto_{int(time.time())}"
        return links[0], extract_filename_from_url(links[0], default)
    return "", ""


@Client.on_message(filters.command("addmonitor") & filters.private)
async def add_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    try:
        if len(message.command) < 3:
            await client.send_message(message.chat.id, "❌ 用法: /addmonitor <频道ID> <关键词1,关键词2>")
            return
        channel_id = int(message.command[1])
        keywords = _parse_keywords(" ".join(message.command[2:]))
        if not keywords:
            await client.send_message(message.chat.id, "❌ 请提供至少一个关键词.")
            return
        record = await asyncio.to_thread(create_monitor, channel_id, keywords)
        await client.send_message(message.chat.id, f"✅ 已添加监控\n{_format_monitor_line(record)}")
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")


@Client.on_message(filters.command("listmonitor") & filters.private)
async def list_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    try:
        records = await asyncio.to_thread(list_monitors)
        if not records:
            await client.send_message(message.chat.id, "ℹ️ 当前没有监控任务.")
            return
        lines = ["📋 当前监控列表:"] + [_format_monitor_line(record) for record in records]
        await client.send_message(message.chat.id, "\n".join(lines))
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")


@Client.on_message(filters.command("togglemonitor") & filters.private)
async def toggle_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    try:
        if len(message.command) < 2:
            await client.send_message(message.chat.id, "❌ 用法: /togglemonitor <监控ID>")
            return
        monitor_id = int(message.command[1])
        record = await asyncio.to_thread(toggle_monitor, monitor_id)
        if not record:
            await client.send_message(message.chat.id, "❌ 未找到对应的监控项.")
            return
        await client.send_message(message.chat.id, f"✅ 状态已更新\n{_format_monitor_line(record)}")
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")


@Client.on_message(filters.command("delmonitor") & filters.private)
async def delete_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    try:
        if len(message.command) < 2:
            await client.send_message(message.chat.id, "❌ 用法: /delmonitor <监控ID>")
            return
        monitor_id = int(message.command[1])
        removed = await asyncio.to_thread(delete_monitor, monitor_id)
        if not removed:
            await client.send_message(message.chat.id, "❌ 未找到对应的监控项.")
            return
        await client.send_message(message.chat.id, "✅ 已删除监控项.")
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")


@Client.on_message(filters.channel)
async def auto_capture_listener(client, message):
    if message.chat is None:
        return
    try:
        monitors = await asyncio.to_thread(get_enabled_monitors_by_channel, message.chat.id)
        if not monitors:
            return
        content = " ".join(part for part in [message.text, message.caption] if part)
        matched, keywords = _match_monitors(monitors, content)
        if not matched:
            return
        source, file_name = _build_source(message)
        if not source or not file_name:
            return
        owner_id = await _resolve_owner()
        if not owner_id:
            await _notify_missing_credentials(client, message, keywords)
            return
        runner = await task_manager.submit(client, owner_id, owner_id, source, file_name)
        channel_title = message.chat.title or str(message.chat.id)
        link = message.link or f"tg://{message.chat.id}/{message.id}"
        summary = f"📡 自动任务已创建\nID: {runner.id}\n频道: {channel_title}\n关键词: {', '.join(keywords) if keywords else '-'}\n来源: {link}\n文件: `{file_name}`"
        sent = await client.send_message(owner_id, summary, reply_markup=_initial_keyboard(runner.id))
        await task_manager.update_message_id(runner.id, sent.message_id)
        await _update_stage(runner.id, "排队中")
        await _notify_admins(client, owner_id, runner.id, message, keywords, file_name, source)
    except Exception as exc:
        LOGGER.error("Auto capture failed: %s", exc)
        owner_id = locals().get("owner_id", 0)
        if owner_id:
            try:
                await client.send_message(owner_id, f"❌ 自动任务创建失败\n{exc}")
            except Exception:
                pass
