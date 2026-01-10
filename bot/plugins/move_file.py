"""Drive 文件移动功能

提供完整的文件和文件夹移动功能，支持跨文件夹移动。
遵循 AGENTS.md 开发规范，使用 AppleUI 设计语言。

Author: AI Agent
Version: 1.0.0
Date: 2026-01-10
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from typing import Optional, Dict, Tuple, List
import logging
import re

# 按照 AGENTS.md 要求导入
from bot.ui_apple_style import AppleUI
from bot import SUDO_USERS
from bot.helpers.utils import CustomFilters
from bot.config import BotCommands, Messages
from bot.modules.drive_helper import get_drive_instance
from bot.helpers.gdrive_utils.credentials_manager import credential_manager

# 日志
LOGGER = logging.getLogger(__name__)

# 命令定义
COMMAND_NAME = "move"
COMMAND_ALIASES = ["move", "mv"]


class MoveFileHandler:
    """
    Drive 文件移动处理器
    
    提供文件和文件夹的移动功能，包括验证、进度显示和错误处理。
    移动操作会改变文件的父文件夹，不会创建副本。
    """
    
    def __init__(self):
        # 存储待确认的移动操作
        self.pending_moves = {}  # {user_id: {source, dest, source_info, dest_info}}
    
    def extract_file_id(self, url: str) -> Optional[str]:
        """
        从 Google Drive URL 提取文件/文件夹 ID
        
        Args:
            url: Drive URL 或直接 ID
            
        Returns:
            文件/文件夹 ID 或 None
        """
        try:
            # 支持多种 URL 格式
            patterns = [
                r'file/d/([a-zA-Z0-9-_]+)',
                r'folders/([a-zA-Z0-9-_]+)',
                r'id=([a-zA-Z0-9-_]+)',
                r'^([a-zA-Z0-9-_]{25,})$',  # 直接 ID
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            LOGGER.error(f"Error extracting file ID: {e}")
            return None
    
    async def get_file_info(
        self,
        user_id: int,
        file_id: str
    ) -> Optional[Dict]:
        """
        获取文件信息
        
        Args:
            user_id: 用户 ID
            file_id: 文件 ID
            
        Returns:
            文件信息字典或 None
        """
        try:
            drive = get_drive_instance(user_id)
            
            file_info = drive.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, parents, webViewLink, createdTime, modifiedTime"
            ).execute()
            
            return file_info
            
        except Exception as e:
            LOGGER.error(f"Get file info failed: {e}")
            return None
    
    async def move_file(
        self,
        user_id: int,
        file_id: str,
        new_parent_id: str
    ) -> Optional[Dict]:
        """
        移动文件到新的父文件夹
        
        Args:
            user_id: 用户 ID
            file_id: 要移动的文件 ID
            new_parent_id: 新的父文件夹 ID
            
        Returns:
            更新后的文件信息或 None
            
        Raises:
            Exception: 移动失败
        """
        try:
            drive = get_drive_instance(user_id)
            
            # 获取当前父文件夹
            file = drive.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # 移动文件（修改父文件夹）
            updated_file = drive.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, name, mimeType, size, webViewLink, parents'
            ).execute()
            
            return updated_file
            
        except Exception as e:
            LOGGER.error(f"Move file failed: {e}")
            raise
    
    def format_file_info_display(self, file_info: Dict) -> str:
        """
        格式化文件信息显示
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            格式化的文本
        """
        # 确定文件类型图标
        mime_type = file_info.get('mimeType', '')
        if 'folder' in mime_type:
            icon = AppleUI.ICONS['folder']
            type_name = "文件夹"
        elif 'document' in mime_type:
            icon = AppleUI.ICONS['document']
            type_name = "文档"
        elif 'video' in mime_type:
            icon = AppleUI.ICONS['video']
            type_name = "视频"
        elif 'image' in mime_type:
            icon = AppleUI.ICONS['image']
            type_name = "图片"
        else:
            icon = AppleUI.ICONS['file']
            type_name = "文件"
        
        name = file_info.get('name', 'Unknown')
        
        # 文件大小
        size = file_info.get('size')
        if size and 'folder' not in mime_type:
            size_str = self._format_size(int(size))
        else:
            size_str = "N/A"
        
        info = f"{icon} **{name}**\n"
        info += f"   • 类型：{type_name}\n"
        info += f"   • 大小：{size_str}"
        
        return info
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


# 全局处理器实例
move_handler = MoveFileHandler()


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    CustomFilters.auth_users
)
async def move_command(
    client: Client, 
    message: Message
) -> None:
    """
    /move 命令处理器
    
    移动文件或文件夹到指定位置。
    
    使用方法：
        /move <source_link> <dest_folder_link>
        /mv <source_link> <dest_folder_link>
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    user_id = message.from_user.id
    
    LOGGER.info(f"User {user_id} triggered /move command")
    
    # 1. 解析参数
    command_parts = message.text.split()
    
    if len(command_parts) < 3:
        # 参数不足
        error_msg = AppleUI.create_error_message(
            error_type="invalid_input",
            details="请提供源文件和目标文件夹链接"
        )
        
        text = AppleUI.format_message(
            title=error_msg["title"],
            icon=error_msg["icon"],
            content=error_msg["message"],
            footer="使用方法：/move <源链接> <目标文件夹链接>"
        )
        
        await message.reply_text(text)
        return
    
    source_url = command_parts[1]
    dest_url = command_parts[2]
    
    # 2. 提取 ID
    source_id = move_handler.extract_file_id(source_url)
    dest_id = move_handler.extract_file_id(dest_url)
    
    if not source_id or not dest_id:
        error_msg = AppleUI.create_error_message(
            error_type="invalid_input",
            details="无法解析文件链接，请确保链接正确"
        )
        
        text = AppleUI.format_message(
            title=error_msg["title"],
            icon=error_msg["icon"],
            content=error_msg["message"]
        )
        
        await message.reply_text(text)
        return
    
    # 3. 发送验证中提示
    validating_text = AppleUI.format_message(
        title="正在验证",
        icon=AppleUI.ICONS["loading"],
        content="正在验证文件和目标位置...\n\n请稍候"
    )
    
    status_msg = await message.reply_text(validating_text)
    
    try:
        # 4. 获取文件信息
        source_info = await move_handler.get_file_info(user_id, source_id)
        dest_info = await move_handler.get_file_info(user_id, dest_id)
        
        if not source_info:
            error_msg = AppleUI.create_error_message(
                error_type="file_not_found",
                details="找不到源文件，请检查链接和权限"
            )
            
            await status_msg.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"]
                )
            )
            return
        
        if not dest_info:
            error_msg = AppleUI.create_error_message(
                error_type="file_not_found",
                details="找不到目标文件夹，请检查链接和权限"
            )
            
            await status_msg.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"]
                )
            )
            return
        
        # 5. 验证目标是文件夹
        if 'folder' not in dest_info.get('mimeType', ''):
            error_msg = AppleUI.create_error_message(
                error_type="invalid_input",
                details="目标必须是文件夹，不能是文件"
            )
            
            await status_msg.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"]
                )
            )
            return
        
        # 6. 检查是否试图移动到当前位置
        current_parents = source_info.get('parents', [])
        if dest_id in current_parents:
            error_msg = AppleUI.create_error_message(
                error_type="invalid_input",
                details="文件已经在目标文件夹中，无需移动"
            )
            
            await status_msg.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"]
                )
            )
            return
        
        # 7. 显示确认对话框（带警告）
        source_display = move_handler.format_file_info_display(source_info)
        dest_display = move_handler.format_file_info_display(dest_info)
        
        is_folder = 'folder' in source_info.get('mimeType', '')
        
        confirm_text = AppleUI.format_message(
            title="⚠️ 确认移动",
            icon=AppleUI.ICONS["warning"],
            content=f"**源（将被移动）：**\n{source_display}\n\n"
                   f"**目标位置：**\n{dest_display}\n\n"
                   f"⚠️ **警告：**\n"
                   f"• 文件将从原位置移动到新位置\n"
                   f"• 原位置将不再有此{('文件夹' if is_folder else '文件')}\n"
                   f"• 此操作不会创建副本\n\n"
                   f"🔒 请仔细确认后再继续"
        )
        
        # 保存待确认的操作
        move_handler.pending_moves[user_id] = {
            'source_id': source_id,
            'dest_id': dest_id,
            'source_info': source_info,
            'dest_info': dest_info
        }
        
        # 创建确认按钮
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button(
                    text="✅ 确认移动",
                    callback_data="move_confirm"
                ),
                AppleUI.create_button(
                    text="❌ 取消",
                    callback_data="move_cancel"
                )
            ]
        ])
        
        await status_msg.edit_text(
            confirm_text,
            reply_markup=keyboard
        )
        
        LOGGER.info(
            f"Move confirmation shown for user {user_id}: "
            f"source={source_info['name']}, dest={dest_info['name']}"
        )
        
    except Exception as e:
        LOGGER.exception(f"Move validation error for user {user_id}")
        
        # 判断错误类型
        if "credentials" in str(e).lower():
            error_type = "auth_failed"
            details = "请先使用 /auth 进行授权"
        elif "permission" in str(e).lower():
            error_type = "permission_denied"
            details = "您没有访问这些文件的权限"
        else:
            error_type = "unknown_error"
            details = str(e)
        
        error_msg = AppleUI.create_error_message(
            error_type=error_type,
            details=details
        )
        
        await status_msg.edit_text(
            AppleUI.format_message(
                title=error_msg["title"],
                icon=error_msg["icon"],
                content=error_msg["message"],
                footer="📞 如问题持续，请联系管理员"
            )
        )


@Client.on_callback_query(filters.regex(r"^move_"))
async def move_callback_handler(
    client: Client,
    callback_query: CallbackQuery
) -> None:
    """
    处理移动相关的回调按钮
    
    回调格式：
        - move_confirm - 确认移动
        - move_cancel - 取消移动
    
    Args:
        client: Pyrogram 客户端
        callback_query: 回调查询对象
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # 取消操作
    if data == "move_cancel":
        # 清除待确认操作
        if user_id in move_handler.pending_moves:
            del move_handler.pending_moves[user_id]
        
        cancel_text = AppleUI.format_message(
            title="已取消",
            icon=AppleUI.ICONS["success"],
            content="移动操作已取消\n\n源文件保持在原位置"
        )
        
        await callback_query.message.edit_text(cancel_text)
        await callback_query.answer("✅ 已取消")
        
        LOGGER.info(f"User {user_id} cancelled move operation")
        return
    
    # 确认移动
    if data == "move_confirm":
        # 获取待确认操作
        if user_id not in move_handler.pending_moves:
            await callback_query.answer("❌ 操作已过期，请重新执行命令")
            return
        
        pending = move_handler.pending_moves[user_id]
        source_id = pending['source_id']
        dest_id = pending['dest_id']
        source_info = pending['source_info']
        dest_info = pending['dest_info']
        
        # 清除待确认操作
        del move_handler.pending_moves[user_id]
        
        try:
            # 显示移动中提示
            await callback_query.answer("⏳ 开始移动...")
            
            is_folder = 'folder' in source_info.get('mimeType', '')
            
            moving_text = AppleUI.format_message(
                title="正在移动",
                icon=AppleUI.ICONS["loading"],
                content=f"**源：** {source_info['name']}\n"
                       f"**目标：** {dest_info['name']}\n\n"
                       f"⏳ 正在处理，请稍候...\n\n"
                       f"{'📁 移动文件夹' if is_folder else '📄 移动文件'}"
            )
            
            await callback_query.message.edit_text(moving_text)
            
            # 执行移动
            moved_file = await move_handler.move_file(
                user_id,
                source_id,
                dest_id
            )
            
            # 显示成功消息
            success_text = AppleUI.format_message(
                title="移动成功",
                icon=AppleUI.ICONS["success"],
                content=f"✅ **{moved_file['name']}** 已成功移动\n\n"
                       f"**类型：** {('文件夹' if is_folder else '文件')}\n"
                       f"**新位置：** {dest_info['name']}\n\n"
                       f"🔗 [在 Drive 中打开]({moved_file['webViewLink']})",
                footer="💡 文件已从原位置移除"
            )
            
            # 创建快捷按钮
            keyboard = AppleUI.create_keyboard([
                [AppleUI.create_button(
                    text="🔗 在 Drive 中打开",
                    url=moved_file['webViewLink']
                )]
            ])
            
            await callback_query.message.edit_text(
                success_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            
            LOGGER.info(
                f"Move completed for user {user_id}: "
                f"{source_info['name']} -> {dest_info['name']}"
            )
            
        except Exception as e:
            LOGGER.exception(f"Move execution error for user {user_id}")
            
            error_msg = AppleUI.create_error_message(
                error_type="unknown_error",
                details=f"移动失败：{str(e)}"
            )
            
            await callback_query.message.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"],
                    footer="📞 如问题持续，请联系管理员"
                )
            )
            
            await callback_query.answer("❌ 移动失败")


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    ~CustomFilters.auth_users
)
async def move_unauthorized(
    client: Client, 
    message: Message
) -> None:
    """
    处理未授权用户的移动请求
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    error_msg = AppleUI.create_error_message(
        error_type="auth_failed",
        details="您需要先授权才能移动文件"
    )
    
    text = AppleUI.format_message(
        title=error_msg["title"],
        icon=error_msg["icon"],
        content=error_msg["message"],
        footer="🔑 使用 /auth 开始授权"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            text="🔑 立即授权",
            callback_data="start_auth"
        )]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)
    
    LOGGER.warning(
        f"Unauthorized move attempt by user {message.from_user.id}"
    )


# 命令帮助
COMMAND_HELP = {
    "command": "move",
    "description": "移动 Google Drive 文件或文件夹",
    "usage": [
        "/move <源链接> <目标文件夹链接> - 移动文件",
        "/mv <源链接> <目标文件夹链接> - 快捷方式"
    ],
    "examples": [
        "/move https://drive.google.com/file/d/xxx https://drive.google.com/drive/folders/yyy",
        "/mv file_id folder_id"
    ],
    "features": [
        "支持文件和文件夹移动",
        "不创建副本（真正的移动）",
        "保留文件元数据",
        "严格的确认机制",
        "安全警告提示",
        "源和目标验证"
    ],
    "notes": [
        "需要先使用 /auth 授权",
        "目标必须是文件夹",
        "需要对源和目标都有访问权限",
        "移动后源位置将不再有该文件",
        "此操作不会创建副本",
        "如需保留原文件，请使用 /copy"
    ],
    "warnings": [
        "⚠️ 移动操作会改变文件位置",
        "⚠️ 原位置将不再有此文件",
        "⚠️ 此操作不可撤销（除非手动移回）",
        "⚠️ 如需保留副本，请使用 /copy 命令"
    ]
}
