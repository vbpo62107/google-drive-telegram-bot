import asyncio
import re
import time
from typing import List, Tuple

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import LOGGER, SUDO_USERS
from bot.config import Messages
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
from bot.helpers.sql_helper.gDriveDB import is_authorized
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
    return f"#{record['id']} 频道: {record['channel_id']} 状态: {status} 关键字: {keywords}"


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
    """Extract media file name from message, including forwarded messages."""
    media = None
    file_name = ""

    # 首先检查直接消息属性
    for attr in ("document", "video", "audio", "animation"):
        media = getattr(message, attr, None)
        if media:
            file_name = getattr(media, "file_name", "") or f"media_{message.chat.id}_{message.id}"
            LOGGER.debug("Found %s media: %s", attr, file_name)
            break

    # 检查照片
    if not media and getattr(message, "photo", None):
        media = message.photo
        file_name = f"photo_{message.chat.id}_{message.id}.jpg"
        LOGGER.debug("Found photo media: %s", file_name)

    # 检查语音
    if not media and getattr(message, "voice", None):
        media = message.voice
        file_name = getattr(media, "file_name", "") or f"voice_{message.chat.id}_{message.id}.ogg"
        LOGGER.debug("Found voice media: %s", file_name)

    # 关键修复：检查转发消息中的视频
    if not media and message.forward_from:
        LOGGER.info("Message is forwarded from user %s, checking forwarded content...", message.forward_from.id)
        # 转发消息的媒体在 message 对象中，需要递归检查
        for attr in ("document", "video", "audio", "animation", "photo", "voice"):
            media = getattr(message, attr, None)
            if media:
                if attr == "photo":
                    file_name = f"forwarded_photo_{message.chat.id}_{message.id}.jpg"
                else:
                    file_name = getattr(media, "file_name", "") or f"forwarded_{attr}_{message.chat.id}_{message.id}"
                LOGGER.info("Found forwarded %s media: %s", attr, file_name)
                break

    # 检查转发的频道消息
    if not media and message.forward_from_chat:
        LOGGER.info("Message is forwarded from channel %s, checking content...", message.forward_from_chat.id)
        for attr in ("document", "video", "audio", "animation", "photo", "voice"):
            media = getattr(message, attr, None)
            if media:
                if attr == "photo":
                    file_name = f"channel_photo_{message.chat.id}_{message.id}.jpg"
                else:
                    file_name = getattr(media, "file_name", "") or f"channel_{attr}_{message.chat.id}_{message.id}"
                LOGGER.info("Found channel-forwarded %s media: %s", attr, file_name)
                break

    if not media:
        LOGGER.debug("No media found in message")
        return ""

    LOGGER.info("_extract_media returning: %s", file_name)
    return file_name


async def _notify_missing_credentials(client: Client, message, keywords: List[str]) -> None:
    channel_title = message.chat.title or str(message.chat.id)
    text = (
        "⚠️ 自动监听触发但缺少有效凭据\n"
        f"频道: {channel_title} ({message.chat.id})\n"
        f"关键字: {', '.join(keywords) if keywords else '-'}\n"
        f"消息ID: {message.id}"
    )
    for admin_id in SUDO_USERS:
        try:
            await client.send_message(admin_id, text)
        except Exception:
            continue


async def _notify_admins(
    client: Client,
    owner_id: int,
    task_id: int,
    message,
    keywords: List[str],
    file_name: str,
    source: str,
) -> None:
    channel_title = message.chat.title or str(message.chat.id)
    link = message.link or f"tg://{message.chat.id}/{message.id}"
    text = (
        "📢 频道触发监控\n"
        f"频道: {channel_title} ({message.chat.id})\n"
        f"关键字: {', '.join(keywords) if keywords else '-'}\n"
        f"任务ID: {task_id}\n"
        f"文件: `{file_name}`\n"
        f"来源: {link}\n"
        f"分配: {owner_id}\n"
        f"源指向: {source}"
    )
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


# @Client.on_message(filters.command("addmonitor") & filters.private)  # 由 __main__.py 注册
async def add_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "⚠️ 您没有权限使用此命令.")
        return
    if not is_authorized(str(message.from_user.id)):
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    try:
        if len(message.command) < 3:
            await client.send_message(message.chat.id, "⚠️ 用法: /addmonitor <频道ID> <关键字,关键字>")
            return
        channel_id = int(message.command[1])
        user_id = message.from_user.id  # 新增：获取添加者的 user_id
        keywords = _parse_keywords(" ".join(message.command[2:]))
        if not keywords:
            await client.send_message(message.chat.id, "⚠️ 请提供至少一个关键词.")
            return
        record = await asyncio.to_thread(create_monitor, channel_id, user_id, keywords)  # 新增：传递 user_id
        LOGGER.info(
            "Monitor added by user %s: id=%s channel=%s keywords=%s",
            message.from_user.id,
            record.get("id"),
            channel_id,
            ", ".join(keywords),
        )
        await client.send_message(message.chat.id, f"✅ 已添加监控\n{_format_monitor_line(record)}")
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")


# @Client.on_message(filters.command("listmonitor") & filters.private)  # 由 __main__.py 注册
async def list_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "⚠️ 您没有权限使用此命令.")
        return
    if not is_authorized(str(message.from_user.id)):
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    try:
        monitors = await asyncio.to_thread(list_monitors)
        if not monitors:
            await message.reply_text("📋 当前没有启用的监控。")
            return

        LOGGER.info(
            "List monitors requested by user %s: count=%s",
            message.from_user.id,
            len(monitors),
        )

        text = "📋 **当前监控列表:**\n\n"
        for monitor in monitors:
            status = "✅ 启用" if monitor["enabled"] else "❌ 禁用"
            keywords = ", ".join(monitor["keywords"]) if monitor["keywords"] else "-"
            creator_id = monitor["user_id"]

            try:
                user = await client.get_chat(creator_id)
                creator_name = f"@{user.username}" if user.username else user.first_name
            except Exception as exc:
                LOGGER.warning("Failed to fetch creator for %s: %s", creator_id, exc)
                creator_name = str(creator_id)

            text += (
                f"🔹 **监听器 #{monitor['id']}**\n"
                f"   👤 创建者: {creator_name}\n"
                f"   📡 频道: `{monitor['channel_id']}`\n"
                f"   ✅ 状态: {status}\n"
                f"   🔑 关键字: `{keywords}`\n\n"
            )

        await message.reply_text(text, quote=True)
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")


# @Client.on_message(filters.command("togglemonitor") & filters.private)  # 由 __main__.py 注册
async def toggle_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "⚠️ 您没有权限使用此命令.")
        return
    if not is_authorized(str(message.from_user.id)):
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    try:
        if len(message.command) < 2:
            await client.send_message(message.chat.id, "⚠️ 用法: /togglemonitor <监控ID>")
            return
        monitor_id = int(message.command[1])
        record = await asyncio.to_thread(toggle_monitor, monitor_id)
        if not record:
            await client.send_message(message.chat.id, "⚠️ 未找到对应的监控项")
            return
        LOGGER.info(
            "Monitor toggled by user %s: id=%s enabled=%s",
            message.from_user.id,
            monitor_id,
            record.get("enabled"),
        )
        await client.send_message(message.chat.id, f"✅ 状态已更新\n{_format_monitor_line(record)}")
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")


# @Client.on_message(filters.command("delmonitor") & filters.private)  # 由 __main__.py 注册
async def delete_monitor_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "⚠️ 您没有权限使用此命令.")
        return
    if not is_authorized(str(message.from_user.id)):
        await client.send_message(message.chat.id, Messages.NOT_AUTH)
        return
    try:
        if len(message.command) < 2:
            await client.send_message(message.chat.id, "⚠️ 用法: /delmonitor <监控ID>")
            return
        monitor_id = int(message.command[1])
        removed = await asyncio.to_thread(delete_monitor, monitor_id)
        if not removed:
            await client.send_message(message.chat.id, "⚠️ 未找到对应的监控项")
            return
        LOGGER.info(
            "Monitor deleted by user %s: id=%s",
            message.from_user.id,
            monitor_id,
        )
        await client.send_message(message.chat.id, "✅ 已删除监控项.")
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")


# @Client.on_message(filters.channel)  # Manually registered in __main__.py
async def auto_capture_listener(client, message):
    """Listen for messages in monitored channels and auto-download media."""
    # 详细日志：记录所有接收到的消息
    LOGGER.info(
        "auto_capture_listener received: chat_id=%s, message_id=%s, "
        "text=%r, caption=%r, has_video=%s, has_document=%s, "
        "is_forwarded=%s",
        message.chat.id if message.chat else None,
        message.id,
        message.text[:50] if message.text else None,
        message.caption[:50] if message.caption else None,
        hasattr(message, "video") and message.video is not None,
        hasattr(message, "document") and message.document is not None,
        message.forward_from is not None or message.forward_from_chat is not None,
    )

    if message.chat is None:
        LOGGER.warning("Message chat is None, returning")
        return

    try:
        monitors = await asyncio.to_thread(get_enabled_monitors_by_channel, message.chat.id)
        LOGGER.info("Found %d monitors for channel %s", len(monitors) if monitors else 0, message.chat.id)

        if not monitors:
            LOGGER.debug("No monitors found for channel %s", message.chat.id)
            return

        content = " ".join(part for part in [message.text, message.caption] if part)

        # 为没有文本/标题的媒体消息添加隐含关键字
        if not content:
            if message.video:
                content = "video"
                LOGGER.info("No text/caption found, detected video media, using 'video' as content")
            elif message.document:
                content = "document"
                LOGGER.info("No text/caption found, detected document media, using 'document' as content")
            elif message.audio:
                content = "audio"
                LOGGER.info("No text/caption found, detected audio media, using 'audio' as content")
            elif message.photo:
                content = "photo"
                LOGGER.info("No text/caption found, detected photo media, using 'photo' as content")
            elif message.voice:
                content = "voice"
                LOGGER.info("No text/caption found, detected voice media, using 'voice' as content")
            else:
                content = "media"
                LOGGER.info("No text/caption found, detected media, using 'media' as content")

        LOGGER.debug("Final content for matching: %r", content[:100] if content else "(empty)")
        matched, keywords = _match_monitors(monitors, content)
        LOGGER.info("Monitor match result: matched=%s, keywords=%s", matched, keywords)

        if not matched:
            LOGGER.debug("No keywords matched")
            return

        source, file_name = _build_source(message)
        LOGGER.info("Build source result: source=%r, file_name=%r", source, file_name)

        if not source or not file_name:
            LOGGER.warning("Source or file_name is empty, cannot proceed")
            return

        owner_id = await _resolve_owner()
        if not owner_id:
            LOGGER.warning("No authorized owner found")
            await _notify_missing_credentials(client, message, keywords)
            return

        # 关键修复确保 task_manager 已初始化并启动 worker
        LOGGER.info("Initializing task_manager...")
        await task_manager.initialize(client)

        runner = await task_manager.submit(client, owner_id, owner_id, source, file_name)
        LOGGER.info("Task created: runner.id=%s, status=%s", runner.id, runner.stage)

        channel_title = message.chat.title or str(message.chat.id)
        link = message.link or f"tg://{message.chat.id}/{message.id}"
        summary = (
            "✅ 自动任务已创建\n"
            f"ID: {runner.id}\n"
            f"频道: {channel_title}\n"
            f"关键字: {', '.join(keywords) if keywords else '-'}\n"
            f"来源: {link}\n"
            f"文件: `{file_name}`"
        )
        sent = await client.send_message(owner_id, summary, reply_markup=_initial_keyboard(runner.id))
        await task_manager.update_message_id(runner.id, sent.id)
        await _update_stage(runner.id, "排队中")
        await _notify_admins(client, owner_id, runner.id, message, keywords, file_name, source)
        LOGGER.info("Auto capture completed successfully: runner.id=%s, file=%s", runner.id, file_name)

    except Exception as exc:
        LOGGER.error("Auto capture failed: %s", exc, exc_info=True)
        owner_id = locals().get("owner_id", 0)

        # 判断错误类型，决定是否重试
        error_msg = str(exc)
        is_retryable = isinstance(exc, (asyncio.TimeoutError, ConnectionError, OSError))

        if owner_id:
            try:
                if is_retryable:
                    retry_msg = (
                        f"⚠️ 自动任务创建失败（可重试）\n"
                        f"错误: {error_msg[:100]}\n"
                        f"系统将在稍后重试"
                    )
                else:
                    retry_msg = (
                        f"❌ 自动任务创建失败\n"
                        f"错误: {error_msg[:100]}\n\n"
                        f"错误类型: {exc.__class__.__name__}\n"
                        f"消息: {message.link or 'N/A'}"
                    )

                await client.send_message(owner_id, retry_msg)
                LOGGER.error("Error message sent to user %s, retryable=%s", owner_id, is_retryable)
            except Exception as send_exc:
                LOGGER.error("Failed to send error message: %s", send_exc)

