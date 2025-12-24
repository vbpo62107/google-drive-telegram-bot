"""
Apple 风格的 Mirror 任务管理界面
提供更优雅的任务创建、进度显示和控制界面
"""

import asyncio
import re
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import DEFAULT_AUTH_MODE, LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import extract_filename_from_url


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: int) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分{seconds % 60}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分"


@Client.on_message(filters.command(["mirror_apple", "ma"]) & filters.private, group=0)
async def mirror_apple_handler(client: Client, message):
    """
    Apple 风格的 Mirror 命令处理器
    使用方式: /mirror_apple <URL>
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
    
    # URL 检查
    if not message.text or len(message.text.split(maxsplit=1)) < 2:
        text = AppleUI.format_message(
            title="镜像任务",
            icon=AppleUI.ICONS["mirroring"],
            content=(
                "**使用方法**\n"
                "`/mirror_apple <URL>`\n\n"
                "**支持的链接**\n"
                "• HTTP/HTTPS 直链\n"
                "• 支持的视频网站\n\n"
                "💡 示例：`/mirror_apple https://example.com/file.zip`"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("查看帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    url = message.text.split(maxsplit=1)[1].strip()
    
    # 验证 URL 格式
    if not re.match(r"^https?://", url, re.I):
        error = AppleUI.create_error_message(
            "invalid_input",
            "仅支持 HTTP/HTTPS 协议\n\n请检查 URL 格式后重试"
        )
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    # 检查授权
    try:
        authorized = gDriveDB.is_authorized(message.from_user.id)
        if not authorized and DEFAULT_AUTH_MODE == "service_account":
            authorized = credential_manager.service_account_available()
    except Exception as exc:
        LOGGER.error("Mirror auth check failed for user %s: %s", message.from_user.id, exc)
        error = AppleUI.create_error_message("network_error")
        text = AppleUI.format_message(
            title=error["title"],
            content="数据库连接错误\n\n请稍后重试"
        )
        await message.reply_text(text)
        return
    
    if not authorized:
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content=(
                "您尚未授权 Google Drive\n\n"
                "请先使用 `/auth` 命令进行授权"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 提取文件名
    filename = extract_filename_from_url(url, "downloaded_file")
    
    # 显示任务创建确认
    text = AppleUI.format_message(
        title="创建镜像任务",
        icon=AppleUI.ICONS["mirroring"],
        content=(
            f"**文件名**\n`{filename}`\n\n"
            f"**源地址**\n`{url[:50]}...`\n\n"
            "确认开始下载并上传到 Google Drive？"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("开始任务", callback_data=f"start_mirror:{url}", icon=AppleUI.ICONS["play"])],
        [AppleUI.create_button("取消", callback_data="cancel_mirror", icon=AppleUI.ICONS["cancel"])]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^start_mirror:"))
async def start_mirror_callback(client: Client, callback_query: CallbackQuery):
    """
    开始镜像任务的回调
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    url = callback_query.data.replace("start_mirror:", "")
    filename = extract_filename_from_url(url, "downloaded_file")
    
    # 显示任务开始消息
    text = AppleUI.format_message(
        title="任务已启动",
        icon=AppleUI.ICONS["processing"],
        content=(
            f"**文件名**\n`{filename}`\n\n"
            "**状态**\n正在准备下载...\n\n"
            "🔄 请稍候，正在获取文件信息"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("暂停", callback_data=f"pause_mirror:1", icon=AppleUI.ICONS["pause"]),
            AppleUI.create_button("取消", callback_data=f"cancel_mirror:1", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 任务已启动")
    
    # 这里应该集成实际的任务管理器
    # 模拟进度更新
    await simulate_mirror_progress(client, callback_query.message, filename)


async def simulate_mirror_progress(client: Client, message, filename: str):
    """
    模拟镜像任务进度（示例）
    实际应用中应集成真实的 task_manager
    """
    total_size = 100 * 1024 * 1024  # 100 MB 示例
    
    for progress in [10, 25, 50, 75, 90, 100]:
        await asyncio.sleep(2)  # 模拟延迟
        
        current_size = int(total_size * progress / 100)
        
        if progress < 50:
            status = "downloading"
            status_text = "正在下载"
        elif progress < 100:
            status = "uploading"
            status_text = "正在上传"
        else:
            status = "completed"
            status_text = "已完成"
        
        text = AppleUI.format_progress(
            current=current_size,
            total=total_size,
            status=status,
            filename=filename,
            speed="2.5 MB/s" if progress < 100 else ""
        )
        
        text += f"\n\n**状态**: {status_text}"
        
        if progress < 100:
            keyboard = AppleUI.create_keyboard([
                [
                    AppleUI.create_button("暂停", callback_data=f"pause_mirror:1", icon=AppleUI.ICONS["pause"]),
                    AppleUI.create_button("取消", callback_data=f"cancel_mirror:1", icon=AppleUI.ICONS["cancel"])
                ]
            ])
        else:
            # 完成后显示成功消息
            success = AppleUI.create_success_message(
                title="上传成功",
                message=f"文件 `{filename}` 已保存到 Google Drive",
                action="查看文件"
            )
            
            text = AppleUI.format_message(
                title=success["title"],
                content=success["message"],
                footer=f"\n📁 大小: {format_file_size(total_size)}"
            )
            
            keyboard = AppleUI.create_keyboard([
                [
                    AppleUI.create_button("查看文件", callback_data="view_file", icon=AppleUI.ICONS["folder"]),
                    AppleUI.create_button("再上传一个", callback_data="upload_another", icon=AppleUI.ICONS["upload"])
                ]
            ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            LOGGER.warning(f"Failed to update progress: {e}")


@Client.on_callback_query(filters.regex(r"^cancel_mirror"))
async def cancel_mirror_callback(client: Client, callback_query: CallbackQuery):
    """
    取消镜像任务
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    text = AppleUI.format_message(
        title="任务已取消",
        icon=AppleUI.ICONS["cancel"],
        content="镜像任务已被取消"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 已取消")


@Client.on_callback_query(filters.regex(r"^pause_mirror:"))
async def pause_mirror_callback(client: Client, callback_query: CallbackQuery):
    """
    暂停镜像任务
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    # 获取任务 ID
    task_id = callback_query.data.split(":")[1]
    
    # 更新按钮为“继续”
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("继续", callback_data=f"resume_mirror:{task_id}", icon=AppleUI.ICONS["play"]),
            AppleUI.create_button("取消", callback_data=f"cancel_mirror:{task_id}", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    # 更新消息
    current_text = callback_query.message.text
    updated_text = current_text.replace("正在下载", "已暂停").replace("正在上传", "已暂停")
    
    await callback_query.message.edit_text(updated_text, reply_markup=keyboard)
    await callback_query.answer("⏸ 已暂停")


@Client.on_callback_query(filters.regex(r"^resume_mirror:"))
async def resume_mirror_callback(client: Client, callback_query: CallbackQuery):
    """
    继续镜像任务
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    task_id = callback_query.data.split(":")[1]
    
    # 更新按钮为“暂停”
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("暂停", callback_data=f"pause_mirror:{task_id}", icon=AppleUI.ICONS["pause"]),
            AppleUI.create_button("取消", callback_data=f"cancel_mirror:{task_id}", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    current_text = callback_query.message.text
    updated_text = current_text.replace("已暂停", "正在继续")
    
    await callback_query.message.edit_text(updated_text, reply_markup=keyboard)
    await callback_query.answer("▶️ 已继续")


@Client.on_callback_query(filters.regex(r"^view_file$"))
async def view_file_callback(client: Client, callback_query: CallbackQuery):
    """
    查看上传的文件
    """
    text = AppleUI.format_message(
        title="文件详情",
        icon=AppleUI.ICONS["file"],
        content=(
            "🔗 **Drive 链接**\n"
            "`https://drive.google.com/file/d/xxx`\n\n"
            "点击上方链接在浏览器中打开"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("在 Drive 中打开", url="https://drive.google.com", icon=AppleUI.ICONS["gdrive"])],
        [AppleUI.create_button("返回", callback_data="back_home", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^upload_another$"))
async def upload_another_callback(client: Client, callback_query: CallbackQuery):
    """
    再上传一个文件
    """
    text = AppleUI.format_message(
        title="镜像任务",
        icon=AppleUI.ICONS["mirroring"],
        content=(
            "**使用方法**\n"
            "`/mirror_apple <URL>`\n\n"
            "💡 示例：`/mirror_apple https://example.com/file.zip`"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
