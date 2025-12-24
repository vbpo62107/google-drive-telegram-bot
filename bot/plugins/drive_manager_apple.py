"""
Apple 风格的 Google Drive 文件管理器
提供克隆、删除、搜索等高级功能
"""

import asyncio
import re
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper.gDriveDB import is_authorized
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
)


def extract_file_id_from_url(url: str) -> Optional[str]:
    """
    从 Google Drive URL 中提取文件 ID
    """
    patterns = [
        r'[-\w]{25,}',  # 直接 ID
        r'/d/([a-zA-Z0-9-_]+)',  # /d/ID 格式
        r'id=([a-zA-Z0-9-_]+)',  # id=ID 格式
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return None


# ==================== 克隆功能 ====================

@Client.on_message(filters.command(["clone_apple", "ca"]) & filters.private, group=0)
async def clone_apple_handler(client: Client, message):
    """
    Apple 风格的 Drive 文件克隆功能
    """
    # 权限检查
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    # 授权检查
    if not is_authorized(str(message.from_user.id)):
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content="请先使用 `/auth_apple` 进行 Google Drive 授权"
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 检查参数
    text_content = message.text or ""
    parts = text_content.split(maxsplit=1)
    
    if len(parts) <= 1 or not parts[1].strip():
        text = AppleUI.format_message(
            title="克隆 Drive 文件",
            icon=AppleUI.ICONS["copy"],
            content=(
                "**使用方法**\n"
                "`/clone_apple <Drive 链接>`\n\n"
                "**支持的链接格式**\n"
                "• `https://drive.google.com/file/d/...`\n"
                "• `https://drive.google.com/folders/d/...`\n\n"
                "💡 示例：`/clone_apple https://drive.google.com/file/d/xxx`"
            )
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("查看帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    link = parts[1].strip()
    
    # 验证链接
    if "drive.google.com" not in link:
        error = AppleUI.create_error_message(
            "invalid_input",
            "请提供有效的 Google Drive 链接"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    # 显示处理中消息
    text = AppleUI.format_message(
        title="正在克隆",
        icon=AppleUI.ICONS["processing"],
        content=(
            f"**源文件**\n`{link[:50]}...`\n\n"
            "正在连接到 Google Drive...\n\n"
            "⏳ 请稍候"
        )
    )
    status = await message.reply_text(text)
    
    try:
        # 获取 Drive 实例
        drive = await get_drive_instance(str(message.from_user.id))
        
        # 更新状态
        text = AppleUI.format_message(
            title="正在克隆",
            icon=AppleUI.ICONS["mirroring"],
            content=(
                f"**源文件**\n`{link[:50]}...`\n\n"
                "正在克隆文件到您的 Drive...\n\n"
                "🔄 处理中"
            )
        )
        await status.edit_text(text)
        
        # 执行克隆
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, drive.clone, link)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="克隆成功",
            message=f"文件已成功克隆到您的 Drive\n\n{result}"
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"]
        )
        
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("打开 Drive", url="https://drive.google.com", icon=AppleUI.ICONS["gdrive"]),
                AppleUI.create_button("再克隆一个", callback_data="clone_another", icon=AppleUI.ICONS["copy"])
            ],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await status.edit_text(text, reply_markup=keyboard)
        
    except DriveAccessError as exc:
        error_msg = drive_error_message(exc.code)
        error = AppleUI.create_error_message("network_error", error_msg)
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await status.edit_text(text)
        
    except Exception as exc:
        LOGGER.exception("Clone failed for user %s: %s", message.from_user.id, exc)
        error = AppleUI.create_error_message(
            "not_found",
            f"克隆失败\n\n`{str(exc)}`"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重试", callback_data="retry_clone", icon=AppleUI.ICONS["refresh"])],
            [AppleUI.create_button("返回", callback_data="back_home", icon=AppleUI.ICONS["back"])]
        ])
        await status.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^clone_another$"))
async def clone_another_callback(client: Client, callback_query: CallbackQuery):
    """再克隆一个文件"""
    text = AppleUI.format_message(
        title="克隆 Drive 文件",
        icon=AppleUI.ICONS["copy"],
        content=(
            "**使用方法**\n"
            "`/clone_apple <Drive 链接>`\n\n"
            "💡 示例：`/clone_apple https://drive.google.com/file/d/xxx`"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# ==================== 删除功能 ====================

@Client.on_message(filters.command(["delete_apple", "da"]) & filters.private, group=0)
async def delete_apple_handler(client: Client, message):
    """
    Apple 风格的 Drive 文件删除功能
    """
    # 权限检查
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    # 授权检查
    if not is_authorized(str(message.from_user.id)):
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content="请先使用 `/auth_apple` 进行 Google Drive 授权"
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 检查参数
    text_content = message.text or ""
    parts = text_content.split(maxsplit=1)
    
    if len(parts) <= 1 or not parts[1].strip():
        text = AppleUI.format_message(
            title="删除 Drive 文件",
            icon=AppleUI.ICONS["delete"],
            content=(
                "**使用方法**\n"
                "`/delete_apple <Drive 链接>`\n\n"
                "**注意**\n"
                "• 删除的文件将移入回收站\n"
                "• 可以在 Drive 中恢复\n\n"
                "💡 示例：`/delete_apple https://drive.google.com/file/d/xxx`"
            )
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("查看帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    link = parts[1].strip()
    
    # 验证链接
    if "drive.google.com" not in link:
        error = AppleUI.create_error_message(
            "invalid_input",
            "请提供有效的 Google Drive 链接"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    # 确认删除
    text = AppleUI.format_message(
        title="确认删除",
        icon=AppleUI.ICONS["warning"],
        content=(
            f"**文件链接**\n`{link[:50]}...`\n\n"
            "确定要删除这个文件吗？\n\n"
            "⚠️ 文件将被移入回收站"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("确认删除", callback_data=f"confirm_delete:{link}", icon=AppleUI.ICONS["delete"]),
            AppleUI.create_button("取消", callback_data="cancel_delete", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^confirm_delete:"))
async def confirm_delete_callback(client: Client, callback_query: CallbackQuery):
    """确认删除文件"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    link = callback_query.data.replace("confirm_delete:", "")
    
    # 显示处理中
    text = AppleUI.format_message(
        title="正在删除",
        icon=AppleUI.ICONS["processing"],
        content="正在删除文件...\n\n⏳ 请稍候"
    )
    await callback_query.message.edit_text(text)
    
    try:
        drive = await get_drive_instance(str(callback_query.from_user.id))
        result = await asyncio.to_thread(drive.delete_file, link)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="删除成功",
            message=f"文件已移入回收站\n\n{result}"
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"],
            footer="💡 您可以在 Drive 中恢复此文件"
        )
        
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("打开回收站", url="https://drive.google.com/drive/trash", icon=AppleUI.ICONS["delete"]),
                AppleUI.create_button("清空回收站", callback_data="empty_trash", icon="🗑")
            ],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("✅ 已删除")
        
    except Exception as exc:
        LOGGER.exception("Delete failed: %s", exc)
        error = AppleUI.create_error_message(
            "network_error",
            f"删除失败\n\n`{str(exc)}`"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await callback_query.message.edit_text(text)
        await callback_query.answer("❌ 删除失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_delete$"))
async def cancel_delete_callback(client: Client, callback_query: CallbackQuery):
    """取消删除"""
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["success"],
        content="删除操作已取消"
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# ==================== 清空回收站 ====================

@Client.on_message(filters.command(["emptytrash_apple", "eta"]) & filters.private, group=0)
async def emptytrash_apple_handler(client: Client, message):
    """
    Apple 风格的清空回收站功能
    """
    # 权限检查
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = AppleUI.format_message(title=error["title"], content=error["message"])
        await message.reply_text(text)
        return
    
    # 授权检查
    if not is_authorized(str(message.from_user.id)):
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content="请先使用 `/auth_apple` 进行 Google Drive 授权"
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 确认清空
    text = AppleUI.format_message(
        title="清空回收站",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要清空 Google Drive 回收站吗？\n\n"
            "⚠️ **注意**\n"
            "• 此操作不可逆！\n"
            "• 回收站中的所有文件将被永久删除\n"
            "• 无法恢复！"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("确认清空", callback_data="confirm_empty_trash", icon=AppleUI.ICONS["delete"]),
            AppleUI.create_button("取消", callback_data="cancel_empty_trash", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^empty_trash$|^confirm_empty_trash$"))
async def empty_trash_callback(client: Client, callback_query: CallbackQuery):
    """确认清空回收站"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    # 如果是从 empty_trash 调用，需要显示确认界面
    if callback_query.data == "empty_trash":
        text = AppleUI.format_message(
            title="清空回收站",
            icon=AppleUI.ICONS["warning"],
            content=(
                "确定要清空 Google Drive 回收站吗？\n\n"
                "⚠️ **注意**\n"
                "• 此操作不可逆！\n"
                "• 回收站中的所有文件将被永久删除"
            )
        )
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("确认清空", callback_data="confirm_empty_trash", icon=AppleUI.ICONS["delete"]),
                AppleUI.create_button("取消", callback_data="cancel_empty_trash", icon=AppleUI.ICONS["cancel"])
            ]
        ])
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
        return
    
    # 显示处理中
    text = AppleUI.format_message(
        title="正在清空",
        icon=AppleUI.ICONS["processing"],
        content="正在清空回收站...\n\n⏳ 请稍候"
    )
    await callback_query.message.edit_text(text)
    
    try:
        drive = await get_drive_instance(str(callback_query.from_user.id))
        msg = await asyncio.to_thread(drive.emptyTrash)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="清空成功",
            message=f"回收站已清空\n\n{msg}"
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"]
        )
        
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("打开 Drive", url="https://drive.google.com", icon=AppleUI.ICONS["gdrive"]),
                AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("✅ 已清空")
        
    except Exception as exc:
        LOGGER.exception("Empty trash failed: %s", exc)
        error = AppleUI.create_error_message(
            "network_error",
            f"清空失败\n\n`{str(exc)}`"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await callback_query.message.edit_text(text)
        await callback_query.answer("❌ 清空失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_empty_trash$"))
async def cancel_empty_trash_callback(client: Client, callback_query: CallbackQuery):
    """取消清空回收站"""
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["success"],
        content="清空操作已取消\n\n您的回收站保持不变"
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
