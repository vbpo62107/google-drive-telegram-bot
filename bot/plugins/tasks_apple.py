"""
Apple 风格的任务管理界面
统一管理所有上传/下载/镜像任务
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI


# 模拟任务数据（实际应用中应从数据库获取）
active_tasks: Dict[int, dict] = {}
task_counter = 0


def create_sample_tasks():
    """创建示例任务数据"""
    global task_counter
    return [
        {
            "id": 1,
            "type": "upload",
            "filename": "document.pdf",
            "status": "uploading",
            "progress": 65,
            "size": 100 * 1024 * 1024,
            "speed": "2.5 MB/s",
            "eta": "2分钟",
        },
        {
            "id": 2,
            "type": "download",
            "filename": "video.mp4",
            "status": "paused",
            "progress": 40,
            "size": 500 * 1024 * 1024,
            "speed": "-",
            "eta": "-",
        },
        {
            "id": 3,
            "type": "mirror",
            "filename": "archive.zip",
            "status": "queued",
            "progress": 0,
            "size": 250 * 1024 * 1024,
            "speed": "-",
            "eta": "排队中",
        },
    ]


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_status_icon(status: str) -> str:
    """获取状态图标"""
    icons = {
        "uploading": "⬆️",
        "downloading": "⬇️",
        "paused": "⏸",
        "queued": "⏳",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "✕",
    }
    return icons.get(status, "🔄")


def get_task_type_name(task_type: str) -> str:
    """获取任务类型名称"""
    names = {
        "upload": "上传",
        "download": "下载",
        "mirror": "镜像",
    }
    return names.get(task_type, "未知")


@Client.on_message(filters.command(["tasks", "t"]) & filters.private, group=0)
async def tasks_handler(client: Client, message):
    """
    Apple 风格的任务管理命令
    """
    if message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        await message.reply_text(text)
        return
    
    await show_tasks_list(client, message)


async def show_tasks_list(client: Client, message, filter_type: str = "all"):
    """
    显示任务列表
    """
    # 获取任务数据（这里使用示例数据）
    tasks = create_sample_tasks()
    
    # 过滤任务
    if filter_type != "all":
        if filter_type == "active":
            tasks = [t for t in tasks if t["status"] in ["uploading", "downloading"]]
        elif filter_type == "paused":
            tasks = [t for t in tasks if t["status"] == "paused"]
        elif filter_type == "queued":
            tasks = [t for t in tasks if t["status"] == "queued"]
    
    if not tasks:
        text = AppleUI.format_message(
            title="任务管理",
            icon=AppleUI.ICONS["info"],
            content=(
                "当前没有任务\n\n"
                "使用以下命令创建任务：\n"
                "• `/mirror_apple` - 镜像任务\n"
                "• 直接发送文件 - 上传任务"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("创建任务", callback_data="create_task", icon=AppleUI.ICONS["upload"])],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        if hasattr(message, 'edit_text'):
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 统计信息
    total = len(tasks)
    active = len([t for t in tasks if t["status"] in ["uploading", "downloading"]])
    paused = len([t for t in tasks if t["status"] == "paused"])
    
    # 构建任务列表
    task_list = []
    for task in tasks[:5]:  # 最多显示 5 个
        icon = get_status_icon(task["status"])
        type_name = get_task_type_name(task["type"])
        
        if task["status"] in ["uploading", "downloading"]:
            task_info = (
                f"{icon} **{task['filename']}**\n"
                f"   {type_name} • {task['progress']}% • {task['speed']}"
            )
        else:
            task_info = (
                f"{icon} **{task['filename']}**\n"
                f"   {type_name} • {task['status'].upper()}"
            )
        
        task_list.append(task_info)
    
    text = AppleUI.format_message(
        title="任务管理",
        icon=AppleUI.ICONS["mirroring"],
        content=(
            f"**总计**: {total} 个任务 • 活动: {active} • 暂停: {paused}\n\n"
            + "\n\n".join(task_list) +
            ("\n\n..." if len(tasks) > 5 else "")
        ),
        footer="点击任务查看详情"
    )
    
    # 按钮布局
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("所有任务", callback_data="filter_all"),
            AppleUI.create_button("活动中", callback_data="filter_active"),
            AppleUI.create_button("已暂停", callback_data="filter_paused")
        ],
        [
            AppleUI.create_button("暂停全部", callback_data="pause_all_tasks", icon=AppleUI.ICONS["pause"]),
            AppleUI.create_button("继续全部", callback_data="resume_all_tasks", icon=AppleUI.ICONS["play"])
        ],
        [AppleUI.create_button("取消全部", callback_data="cancel_all_tasks", icon=AppleUI.ICONS["cancel"])],
        [AppleUI.create_button("刷新", callback_data="refresh_tasks", icon=AppleUI.ICONS["refresh"])],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^filter_(all|active|paused|queued)$"))
async def filter_tasks_callback(client: Client, callback_query: CallbackQuery):
    """过滤任务列表"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    filter_type = callback_query.data.replace("filter_", "")
    await show_tasks_list(client, callback_query.message, filter_type)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^pause_all_tasks$"))
async def pause_all_tasks_callback(client: Client, callback_query: CallbackQuery):
    """暂停所有任务"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    # 实际应用中应调用任务管理器
    await callback_query.answer("⏸ 已暂停所有活动任务", show_alert=True)
    await show_tasks_list(client, callback_query.message)


@Client.on_callback_query(filters.regex(r"^resume_all_tasks$"))
async def resume_all_tasks_callback(client: Client, callback_query: CallbackQuery):
    """继续所有任务"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    await callback_query.answer("▶️ 已继续所有暂停任务", show_alert=True)
    await show_tasks_list(client, callback_query.message)


@Client.on_callback_query(filters.regex(r"^cancel_all_tasks$"))
async def cancel_all_tasks_callback(client: Client, callback_query: CallbackQuery):
    """取消所有任务确认"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    text = AppleUI.format_message(
        title="取消所有任务",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要取消所有正在进行的任务吗？\n\n"
            "⚠️ 此操作不可撤销\n"
            "所有进度将丢失"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("确认取消", callback_data="confirm_cancel_all", icon=AppleUI.ICONS["delete"])],
        [AppleUI.create_button("返回", callback_data="refresh_tasks", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^confirm_cancel_all$"))
async def confirm_cancel_all_callback(client: Client, callback_query: CallbackQuery):
    """确认取消所有任务"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    # 实际应用中应调用任务管理器取消所有任务
    
    success = AppleUI.create_success_message(
        title="已取消",
        message="所有任务已被取消"
    )
    
    text = AppleUI.format_message(
        title=success["title"],
        content=success["message"]
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("查看任务", callback_data="refresh_tasks", icon=AppleUI.ICONS["mirroring"])],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 已取消所有任务")


@Client.on_callback_query(filters.regex(r"^refresh_tasks$"))
async def refresh_tasks_callback(client: Client, callback_query: CallbackQuery):
    """刷新任务列表"""
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 无权操作", show_alert=True)
        return
    
    await show_tasks_list(client, callback_query.message)
    await callback_query.answer("✅ 已刷新")


@Client.on_callback_query(filters.regex(r"^create_task$"))
async def create_task_callback(client: Client, callback_query: CallbackQuery):
    """创建新任务"""
    text = AppleUI.format_message(
        title="创建任务",
        icon=AppleUI.ICONS["upload"],
        content=(
            "选择要创建的任务类型：\n\n"
            "**镜像任务**\n"
            "从 URL 下载并上传到 Drive\n"
            "`/mirror_apple <URL>`\n\n"
            "**上传任务**\n"
            "直接发送文件给机器人"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("镜像任务", callback_data="help_mirror", icon=AppleUI.ICONS["mirroring"])],
        [AppleUI.create_button("返回任务列表", callback_data="refresh_tasks", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^help_mirror$"))
async def help_mirror_callback(client: Client, callback_query: CallbackQuery):
    """镜像任务帮助"""
    text = AppleUI.format_message(
        title="镜像任务",
        icon=AppleUI.ICONS["mirroring"],
        content=(
            "**使用方法**\n"
            "`/mirror_apple <URL>`\n\n"
            "**支持的链接**\n"
            "• HTTP/HTTPS 直链\n"
            "• 支持的视频网站\n\n"
            "**示例**\n"
            "`/mirror_apple https://example.com/file.zip`"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("查看详细帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])],
        [AppleUI.create_button("返回", callback_data="create_task", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# 定时更新任务状态（示例）
async def task_status_updater(client: Client, chat_id: int, message_id: int, task_id: int):
    """
    定时更新任务状态（示例功能）
    实际应用中应从任务管理器获取实时状态
    """
    for progress in range(0, 101, 10):
        await asyncio.sleep(1)
        
        text = AppleUI.format_progress(
            current=progress * 1024 * 1024,
            total=100 * 1024 * 1024,
            status="uploading",
            filename="example.pdf",
            speed="2.5 MB/s" if progress < 100 else ""
        )
        
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
        except Exception as e:
            LOGGER.warning(f"Failed to update task status: {e}")
            break
