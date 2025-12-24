"""
Google Drive Set Folder Command - Apple Design Edition
Google Drive 设置文件夹命令 - Apple 设计版

使用 AppleUI 组件提供优雅的用户界面。
"""
import asyncio
from typing import Tuple

from pyrogram import Client, filters
from pyrogram.types import Message

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
from bot.ui.apple_ui import AppleUI


async def _set_parent(client: Client, message: Message) -> None:
    """
    处理 /setfolder 命令，设置默认上传文件夹
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    user_id = message.from_user.id

    # 如果没有提供参数，显示当前设置
    if len(message.command) <= 1:
        current_parent = idsDB.search_parent(user_id)
        
        if current_parent:
            await AppleUI.send_info(
                client,
                message.chat.id,
                "📂 当前文件夹",
                "您已设置了默认上传文件夹。",
                f"**文件夹 ID：** `{current_parent}`\n\n"
                f"**修改设置：**\n"
                f"`/{BotCommands.SetFolder[0]} <新文件夹链接>`\n\n"
                f"**清除设置：**\n"
                f"`/{BotCommands.SetFolder[0]} clear`",
            )
        else:
            await AppleUI.send_info(
                client,
                message.chat.id,
                "📂 设置文件夹",
                "您尚未设置默认上传文件夹。",
                f"**设置文件夹：**\n"
                f"`/{BotCommands.SetFolder[0]} <文件夹链接>`\n\n"
                f"**示例：**\n"
                f"`/{BotCommands.SetFolder[0]} https://drive.google.com/drive/folders/xxx`\n\n"
                f"ℹ️ 设置后，所有上传的文件将保存到此文件夹。",
            )
        return

    link = message.command[1]

    # 处理清除命令
    if "clear" in link.lower():
        current_parent = idsDB.search_parent(user_id)
        
        if current_parent:
            idsDB._clear(user_id)
            invalidate_drive_instance(user_id)
            
            await AppleUI.send_success(
                client,
                message.chat.id,
                "🧹 已清除设置",
                "默认上传文件夹已成功清除。",
                f"**原文件夹 ID：** `{current_parent}`\n\n"
                f"现在文件将上传到根目录。\n\n"
                f"要重新设置，请使用：\n"
                f"`/{BotCommands.SetFolder[0]} <文件夹链接>`",
            )
        else:
            await AppleUI.send_info(
                client,
                message.chat.id,
                "ℹ️ 无需清除",
                "您当前没有设置默认文件夹。",
                f"要设置文件夹，请使用：\n"
                f"`/{BotCommands.SetFolder[0]} <文件夹链接>`",
            )
        return

    # 显示验证状态
    sent_message = await AppleUI.send_processing(
        client,
        message.chat.id,
        "🔍 验证链接",
        "正在验证 Google Drive 文件夹链接...",
        f"**目标链接：** `{link}`",
    )

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

    # 验证文件夹链接
    try:
        result, file_id = await asyncio.to_thread(drive.checkFolderLink, link)
        
        if result:
            # 链接有效，保存设置
            idsDB._set(user_id, file_id)
            LOGGER.info("SetParent:%s: %s", user_id, file_id)
            invalidate_drive_instance(user_id)
            
            await client.edit_message_text(
                message.chat.id,
                sent_message.id,
                AppleUI.format_message(
                    "✅ 设置成功",
                    "默认上传文件夹已成功设置。",
                    f"**文件夹 ID：** `{file_id}`\n\n"
                    f"现在所有上传的文件将保存到此文件夹。\n\n"
                    f"**修改设置：**\n"
                    f"`/{BotCommands.SetFolder[0]} <新链接>`\n\n"
                    f"**清除设置：**\n"
                    f"`/{BotCommands.SetFolder[0]} clear`",
                ),
            )
        else:
            # 链接无效
            await client.edit_message_text(
                message.chat.id,
                sent_message.id,
                AppleUI.format_message(
                    "❌ 链接无效",
                    "提供的不是有效的 Google Drive 文件夹链接。",
                    f"{file_id}\n\n"
                    f"**请确保：**\n"
                    f"• 这是一个文件夹链接（不是文件）\n"
                    f"• 链接格式正确\n"
                    f"• 您有访问权限\n"
                    f"• 文件夹存在且未被删除",
                ),
            )
            
    except IndexError:
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ 链接格式错误",
                "无法解析 Google Drive 链接。",
                f"**请检查：**\n"
                f"• 链接是否完整\n"
                f"• 是否是文件夹分享链接\n\n"
                f"**正确格式：**\n"
                f"`https://drive.google.com/drive/folders/xxxxxx`",
            ),
        )
    except Exception as exc:
        await client.edit_message_text(
            message.chat.id,
            sent_message.id,
            AppleUI.format_message(
                "❌ 验证失败",
                "验证文件夹链接时发生错误。",
                f"**错误详情：** {str(exc)}\n\n"
                f"请稍后重试或检查网络连接。",
            ),
        )


# 导出处理器
setfolder_handler = _set_parent
