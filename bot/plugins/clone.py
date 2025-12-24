"""
Google Drive Clone Command - Apple Design Edition
克隆 Google Drive 文件命令 - Apple 设计版

使用 AppleUI 组件提供优雅的用户界面。
"""
import asyncio
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from bot import SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper.gDriveDB import is_authorized
from bot.helpers.utils import CustomFilters
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
)
from bot.ui.apple_ui import AppleUI


async def clone_handler(client: Client, message: Message) -> Optional[str]:
    """
    处理 /clone 命令，克隆 Google Drive 文件
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
        
    Returns:
        克隆结果消息，失败返回 None
    """
    # 权限检查
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "权限不足",
            "您没有权限使用此命令。",
            "仅授权用户可以克隆文件。",
        )
        return None

    # 授权检查
    if not is_authorized(str(message.from_user.id)):
        await AppleUI.send_error(
            client,
            message.chat.id,
            "未授权访问",
            "您尚未授权 Google Drive 访问权限。",
            "请使用 /auth 命令完成授权。",
        )
        return None

    # 解析命令参数
    text = message.text or ""
    parts = text.split(maxsplit=1)
    
    if len(parts) <= 1 or not parts[1].strip():
        await AppleUI.send_info(
            client,
            message.chat.id,
            "使用说明",
            f"请提供要克隆的 Google Drive 链接。",
            f"**格式：** `/{BotCommands.Clone[0]} <Drive链接>`\n\n"
            f"**示例：**\n"
            f"`/{BotCommands.Clone[0]} https://drive.google.com/file/d/xxx`",
        )
        return None

    link = parts[1].strip()

    # 获取 Drive 实例
    try:
        drive = await get_drive_instance(str(message.from_user.id))
    except DriveAccessError as exc:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "Drive 访问错误",
            drive_error_message(exc.code),
            "请检查您的授权状态或稍后重试。",
        )
        return None
    except Exception as exc:
        await AppleUI.send_error(
            client,
            message.chat.id,
            "初始化失败",
            str(exc),
            "无法连接到 Google Drive 服务。",
        )
        return None

    # 显示处理状态
    status = await AppleUI.send_processing(
        client,
        message.chat.id,
        "克隆文件中",
        f"正在克隆文件到您的 Google Drive...",
        f"**源链接：** `{link}`",
        reply_to_message_id=message.id,
    )

    # 执行克隆操作
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, drive.clone, link)
        
        # 成功通知
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "✅ 克隆完成",
                "文件已成功克隆到您的 Google Drive。",
                result,
            ),
        )
        return result
        
    except Exception as exc:
        # 错误通知
        error_msg = str(exc)
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "❌ 克隆失败",
                "克隆文件时发生错误。",
                f"**错误详情：** {error_msg}\n\n"
                f"**可能原因：**\n"
                f"• 链接无效或已过期\n"
                f"• 没有访问权限\n"
                f"• 文件已被删除\n"
                f"• 网络连接问题",
            ),
        )
        return None
