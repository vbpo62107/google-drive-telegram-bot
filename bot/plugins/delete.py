"""
Google Drive Delete Command - Apple Design Edition
Google Drive 删除命令 - Apple 设计版

使用 AppleUI 组件提供优雅的用户界面。
"""
import asyncio
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.utils import CustomFilters
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
)
from bot.helpers.sql_helper.gDriveDB import is_authorized
from bot.ui.apple_ui import AppleUI


async def _delete(client: Client, message: Message) -> None:
    """
    处理 /delete 命令，删除 Google Drive 文件
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    user = message.from_user
    
    # 权限检查
    if user is None or user.id not in SUDO_USERS:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "权限不足",
            "您没有权限使用此命令。",
            "仅授权用户可以删除文件。",
        )
        return

    # 授权检查
    if not is_authorized(str(user.id)):
        await AppleUI.send_error(
            client,
            message.chat.id,
            "未授权访问",
            "您尚未授权 Google Drive 访问权限。",
            "请使用 /auth 命令完成授权。",
        )
        return

    user_id = user.id

    # 解析命令参数
    if not (len(message.command) > 1 or message.reply_to_message):
        await AppleUI.send_info(
            client,
            message.chat.id,
            "使用说明",
            "请提供要删除的 Google Drive 链接。",
            f"**方式一：** `/{BotCommands.Delete[0]} <Drive链接>`\n"
            f"**方式二：** 回复包含链接的消息\n\n"
            f"**示例：**\n"
            f"`/{BotCommands.Delete[0]} https://drive.google.com/file/d/xxx`",
        )
        return

    # 显示检查状态
    sent_message = await AppleUI.send_processing(
        client,
        message.chat.id,
        "检查链接",
        "正在验证 Google Drive 链接...",
        "请稍候，这只需要几秒钟。",
    )

    # 获取链接
    if len(message.command) > 1:
        link = message.command[1]
    elif (
        message.reply_to_message
        and message.reply_to_message.entities
        and len(message.reply_to_message.entities) > 1
        and message.reply_to_message.entities[1].url
    ):
        link = message.reply_to_message.entities[1].url
    else:
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ 链接缺失",
                "未找到有效的 Google Drive 链接。",
                f"请使用：`/{BotCommands.Delete[0]} <链接>`",
            ),
        )
        return

    LOGGER.info("Delete:%s: %s", user_id, link)

    # 获取 Drive 实例
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ Drive 访问错误",
                drive_error_message(exc.code),
                "请检查您的授权状态或稍后重试。",
            ),
        )
        return
    except Exception as exc:
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ 初始化失败",
                str(exc),
                "无法连接到 Google Drive 服务。",
            ),
        )
        return

    # 更新为删除状态
    await client.edit_message_text(
        message.chat.id,
        sent_message.id,
        AppleUI.format_message(
            "🗑️ 删除中",
            "正在删除文件...",
            f"**目标：** `{link}`",
        ),
    )

    # 执行删除操作
    try:
        result = await asyncio.to_thread(drive.delete_file, link)
        
        # 成功通知
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "✅ 删除完成",
                "文件已成功从 Google Drive 中删除。",
                result,
            ),
        )
    except Exception as exc:
        # 错误通知
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ 删除失败",
                "删除文件时发生错误。",
                f"**错误详情：** {str(exc)}\n\n"
                f"**可能原因：**\n"
                f"• 没有删除权限\n"
                f"• 文件已经被删除\n"
                f"• 链接无效或过期",
            ),
        )


async def _emptyTrash(client: Client, message: Message) -> None:
    """
    处理 /emptytrash 命令，清空 Google Drive 回收站
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    user = message.from_user
    
    # 权限检查
    if user is None or user.id not in SUDO_USERS:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "权限不足",
            "您没有权限使用此命令。",
            "仅授权用户可以清空回收站。",
        )
        return

    # 授权检查
    if not is_authorized(str(user.id)):
        await AppleUI.send_error(
            client,
            message.chat.id,
            "未授权访问",
            "您尚未授权 Google Drive 访问权限。",
            "请使用 /auth 命令完成授权。",
        )
        return

    user_id = user.id
    LOGGER.info("EmptyTrash: %s", user_id)

    # 获取 Drive 实例
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "Drive 访问错误",
            drive_error_message(exc.code),
            "请检查您的授权状态或稍后重试。",
        )
        return
    except Exception as exc:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "初始化失败",
            str(exc),
            "无法连接到 Google Drive 服务。",
        )
        return

    # 显示处理状态
    status = await AppleUI.send_processing(
        client,
        message.chat.id,
        "🗑️ 清空回收站",
        "正在清空 Google Drive 回收站...",
        "⚠️ **注意：**此操作不可恢复，请确认后再继续。",
    )

    # 执行清空操作
    try:
        msg = await asyncio.to_thread(drive.emptyTrash)
        
        # 成功通知
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "✅ 清空完成",
                "回收站已成功清空。",
                msg,
            ),
        )
    except Exception as exc:
        # 错误通知
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "❌ 清空失败",
                "清空回收站时发生错误。",
                f"**错误详情：** {str(exc)}\n\n"
                f"请稍后重试或联系管理员。",
            ),
        )


# 导出处理器
delete_handler = _delete
emptytrash_handler = _emptyTrash
