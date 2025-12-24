"""
Apple 风格的 Google Drive 搜索和文件管理界面
提侟直观的文件搜索和管理功能
"""

import re
from datetime import datetime
from typing import List, Dict, Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper import gDriveDB


# 模拟搜索结果（实际应集成 Google Drive API）
MOCK_FILES = [
    {
        "id": "1abc",
        "name": "Project Proposal.pdf",
        "size": 2457600,  # 2.4 MB
        "mimeType": "application/pdf",
        "modifiedTime": "2025-12-20T10:30:00Z",
        "shared": False,
    },
    {
        "id": "2def",
        "name": "Design Assets",
        "size": 0,
        "mimeType": "application/vnd.google-apps.folder",
        "modifiedTime": "2025-12-22T14:15:00Z",
        "shared": True,
    },
    {
        "id": "3ghi",
        "name": "Meeting Recording.mp4",
        "size": 157286400,  # 150 MB
        "mimeType": "video/mp4",
        "modifiedTime": "2025-12-23T09:00:00Z",
        "shared": False,
    },
]


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "-"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_date(date_str: str) -> str:
    """格式化日期"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        
        if diff.days == 0:
            return "今天"
        elif diff.days == 1:
            return "昨天"
        elif diff.days < 7:
            return f"{diff.days} 天前"
        else:
            return dt.strftime("%Y-%m-%d")
    except:
        return "未知"


def get_file_icon(mime_type: str) -> str:
    """根据 MIME 类型返回图标"""
    if "folder" in mime_type:
        return AppleUI.ICONS["folder"]
    elif "pdf" in mime_type:
        return "📝"
    elif "image" in mime_type:
        return "🖼"
    elif "video" in mime_type:
        return "🎥"
    elif "audio" in mime_type:
        return "🎵"
    elif "text" in mime_type or "document" in mime_type:
        return "📄"
    elif "sheet" in mime_type:
        return "📈"
    elif "presentation" in mime_type:
        return "📊"
    else:
        return AppleUI.ICONS["file"]


@Client.on_message(filters.command(["search_apple", "sda"]) & filters.private, group=0)
async def search_apple_handler(client: Client, message):
    """
    Apple 风格的 Drive 搜索命令
    """
    user_id = message.from_user.id
    
    # 检查授权
    try:
        is_authorized = gDriveDB.is_authorized(user_id)
    except:
        is_authorized = False
    
    if not is_authorized:
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 检查是否提供了搜索关键词
    if not message.text or len(message.text.split(maxsplit=1)) < 2:
        text = AppleUI.format_message(
            title="搜索 Drive 文件",
            icon=AppleUI.ICONS["search"],
            content=(
                "**使用方法**\n"
                "`/search_apple <关键词>`\n\n"
                "**搜索提示**\n"
                "• 支持文件名搜索\n"
                "• 支持文件类型筛选\n"
                "• 大小写不敏感\n\n"
                "💡 示例：`/search_apple project`"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("浏览所有文件", callback_data="browse_files", icon=AppleUI.ICONS["folder"])],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        return
    
    # 获取搜索关键词
    query = message.text.split(maxsplit=1)[1].strip()
    
    # 执行搜索
    await perform_search(client, message, query)


async def perform_search(client: Client, message, query: str):
    """
    执行搜索并显示结果
    """
    # 显示搜索中
    text = AppleUI.format_message(
        title="正在搜索",
        icon=AppleUI.ICONS["processing"],
        content=f"搜索关键词: `{query}`\n\n⏳ 请稍候..."
    )
    
    if hasattr(message, 'edit_text'):
        sent = message
        await message.edit_text(text)
    else:
        sent = await message.reply_text(text)
    
    # 模拟搜索（实际应调用 Google Drive API）
    results = [f for f in MOCK_FILES if query.lower() in f["name"].lower()]
    
    if not results:
        # 无结果
        text = AppleUI.format_message(
            title="未找到结果",
            icon=AppleUI.ICONS["error"],
            content=(
                f"未找到包含 `{query}` 的文件\n\n"
                "**搜索建议**\n"
                "• 检查拼写\n"
                "• 尝试使用更通用的关键词\n"
                "• 浏览所有文件列表"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("浏览所有文件", callback_data="browse_files", icon=AppleUI.ICONS["folder"])],
            [AppleUI.create_button("重新搜索", callback_data="search_again", icon=AppleUI.ICONS["search"])]
        ])
        
        await sent.edit_text(text, reply_markup=keyboard)
    else:
        # 显示结果
        await show_search_results(sent, query, results)


async def show_search_results(message, query: str, results: List[Dict]):
    """
    显示搜索结果列表
    """
    result_count = len(results)
    
    # 构建结果列表
    result_lines = []
    for idx, file in enumerate(results[:10], 1):  # 最多显示 10 个
        icon = get_file_icon(file["mimeType"])
        size = format_file_size(file["size"])
        date = format_date(file["modifiedTime"])
        shared_icon = " 🔗" if file.get("shared") else ""
        
        result_lines.append(
            f"{icon} **{file['name']}**{shared_icon}\n"
            f"   {size} • {date}"
        )
    
    results_text = "\n\n".join(result_lines)
    
    text = AppleUI.format_message(
        title=f"搜索结果 ({result_count})",
        icon=AppleUI.ICONS["search"],
        subtitle=f"关键词: {query}",
        content=results_text,
        footer=f"\n💡 点击下方按钮查看详情" if result_count > 0 else ""
    )
    
    # 为每个结果创建按钮（最多 3 个）
    buttons = []
    for idx, file in enumerate(results[:3], 1):
        icon = get_file_icon(file["mimeType"])
        buttons.append([
            AppleUI.create_button(
                f"{icon} {file['name'][:20]}...",
                callback_data=f"file_details:{file['id']}",
                icon=""
            )
        ])
    
    buttons.append([
        AppleUI.create_button("重新搜索", callback_data="search_again", icon=AppleUI.ICONS["search"]),
        AppleUI.create_button("浏览全部", callback_data="browse_files", icon=AppleUI.ICONS["folder"])
    ])
    
    keyboard = AppleUI.create_keyboard(buttons)
    
    await message.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^file_details:"))
async def file_details_callback(client: Client, callback_query: CallbackQuery):
    """
    显示文件详情
    """
    file_id = callback_query.data.split(":")[1]
    
    # 查找文件
    file = next((f for f in MOCK_FILES if f["id"] == file_id), None)
    
    if not file:
        await callback_query.answer("文件未找到", show_alert=True)
        return
    
    # 文件详情
    icon = get_file_icon(file["mimeType"])
    size = format_file_size(file["size"])
    date = format_date(file["modifiedTime"])
    is_folder = "folder" in file["mimeType"]
    
    text = AppleUI.format_message(
        title=file["name"],
        icon=icon,
        content=(
            f"**类型**\n"
            f"{'文件夹' if is_folder else '文件'}\n\n"
            f"**大小**\n"
            f"{size}\n\n"
            f"**修改时间**\n"
            f"{date}\n\n"
            f"**共享状态**\n"
            f"{'\u2705 已共享' if file.get('shared') else '\u274c 私有'}\n\n"
            f"**文件 ID**\n"
            f"`{file['id']}`"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("在 Drive 中打开", url=f"https://drive.google.com/file/d/{file['id']}", icon=AppleUI.ICONS["gdrive"]),
        ],
        [
            AppleUI.create_button("共享", callback_data=f"share_file:{file_id}", icon=AppleUI.ICONS["link"]),
            AppleUI.create_button("删除", callback_data=f"delete_file:{file_id}", icon=AppleUI.ICONS["delete"])
        ],
        [AppleUI.create_button("返回搜索", callback_data="back_to_search", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^browse_files$"))
async def browse_files_callback(client: Client, callback_query: CallbackQuery):
    """
    浏览所有文件
    """
    # 显示所有文件
    await show_search_results(callback_query.message, "所有文件", MOCK_FILES)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^search_again$"))
async def search_again_callback(client: Client, callback_query: CallbackQuery):
    """
    重新搜索
    """
    text = AppleUI.format_message(
        title="搜索 Drive 文件",
        icon=AppleUI.ICONS["search"],
        content=(
            "请使用以下命令搜索：\n\n"
            "`/search_apple <关键词>`\n\n"
            "💡 示例：`/search_apple project`"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^share_file:"))
async def share_file_callback(client: Client, callback_query: CallbackQuery):
    """
    共享文件
    """
    file_id = callback_query.data.split(":")[1]
    file = next((f for f in MOCK_FILES if f["id"] == file_id), None)
    
    if not file:
        await callback_query.answer("文件未找到", show_alert=True)
        return
    
    # 模拟共享链接
    share_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    
    text = AppleUI.format_message(
        title="共享文件",
        icon=AppleUI.ICONS["link"],
        content=(
            f"**{file['name']}**\n\n"
            "共享链接已生成：\n\n"
            f"`{share_link}`\n\n"
            "🔒 任何拥有此链接的人都可以查看此文件"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("复制链接", url=share_link, icon=AppleUI.ICONS["copy"])],
        [AppleUI.create_button("返回", callback_data=f"file_details:{file_id}", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 共享链接已生成")


@Client.on_callback_query(filters.regex(r"^delete_file:"))
async def delete_file_callback(client: Client, callback_query: CallbackQuery):
    """
    删除文件确认
    """
    file_id = callback_query.data.split(":")[1]
    file = next((f for f in MOCK_FILES if f["id"] == file_id), None)
    
    if not file:
        await callback_query.answer("文件未找到", show_alert=True)
        return
    
    text = AppleUI.format_message(
        title="确认删除",
        icon=AppleUI.ICONS["warning"],
        content=(
            f"确定要删除以下文件吗？\n\n"
            f"**{file['name']}**\n\n"
            "⚠️ 文件将移动到回收站\n"
            "您可以在 30 天内恢复"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("确认删除", callback_data=f"confirm_delete:{file_id}", icon=AppleUI.ICONS["delete"])],
        [AppleUI.create_button("取消", callback_data=f"file_details:{file_id}", icon=AppleUI.ICONS["cancel"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^confirm_delete:"))
async def confirm_delete_callback(client: Client, callback_query: CallbackQuery):
    """
    确认删除文件
    """
    file_id = callback_query.data.split(":")[1]
    file = next((f for f in MOCK_FILES if f["id"] == file_id), None)
    
    if not file:
        await callback_query.answer("文件未找到", show_alert=True)
        return
    
    # 模拟删除
    success = AppleUI.create_success_message(
        title="已删除",
        message=f"文件 `{file['name']}` 已移动到回收站",
        action="完成"
    )
    
    text = AppleUI.format_message(
        title=success["title"],
        content=success["message"],
        footer="\n💡 您可以在 Google Drive 回收站中恢复此文件"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回搜索", callback_data="search_again", icon=AppleUI.ICONS["search"])],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 已删除")


# Inline Query 支持（快速搜索）
@Client.on_inline_query()
async def inline_search_handler(client: Client, inline_query: InlineQuery):
    """
    Inline 模式快速搜索
    使用方式：@bot_username <搜索关键词>
    """
    query = inline_query.query.strip()
    
    if not query:
        # 显示提示
        results = [
            InlineQueryResultArticle(
                title="🔍 搜索 Google Drive",
                description="输入关键词开始搜索...",
                input_message_content=InputTextMessageContent(
                    message_text="请输入搜索关键词"
                )
            )
        ]
    else:
        # 搜索文件
        matched_files = [f for f in MOCK_FILES if query.lower() in f["name"].lower()]
        
        results = []
        for file in matched_files[:10]:
            icon = get_file_icon(file["mimeType"])
            size = format_file_size(file["size"])
            
            results.append(
                InlineQueryResultArticle(
                    title=f"{icon} {file['name']}",
                    description=f"{size} • {format_date(file['modifiedTime'])}",
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"**{file['name']}**\n\n"
                            f"🔗 https://drive.google.com/file/d/{file['id']}"
                        )
                    )
                )
            )
        
        if not results:
            results = [
                InlineQueryResultArticle(
                    title="❓ 未找到结果",
                    description=f"未找到包含 '{query}' 的文件",
                    input_message_content=InputTextMessageContent(
                        message_text=f"未找到包含 '{query}' 的文件"
                    )
                )
            ]
    
    try:
        await inline_query.answer(
            results=results,
            cache_time=10,
            is_personal=True
        )
    except Exception as e:
        LOGGER.error(f"Inline query error: {e}")
