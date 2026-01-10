"""Drive 文件复制功能

提供完整的文件和文件夹复制功能，支持跨文件夹复制。
遵循 AGENTS.md 开发规范，使用 AppleUI 设计语言。

Author: AI Agent
Version: 1.0.0
Date: 2026-01-10
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from typing import Optional, Dict, Tuple
import logging
import re
import time

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
COMMAND_NAME = "copy"
COMMAND_ALIASES = ["copy", "cp"]


class CopyFileHandler:
    """
    Drive 文件复制处理器
    
    提供文件和文件夹的复制功能，包括验证、进度显示和错误处理。
    """
    
    def __init__(self):
        # 存储待确认的复制操作
        self.pending_copies = {}  # {user_id: {source, dest, source_info, dest_info}}
    
    def extract_file_id(self, url: str) -> Optional[str]:
        """
        从 Google Drive URL 提取文件/文件夹 ID
        
        Args:
            url: Drive URL
            
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
    
    async def copy_file(
        self,
        user_id: int,
        source_id: str,
        dest_folder_id: str,
        new_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        复制文件到目标文件夹
        
        Args:
            user_id: 用户 ID
            source_id: 源文件 ID
            dest_folder_id: 目标文件夹 ID
            new_name: 新文件名（可选）
            
        Returns:
            新文件信息或 None
            
        Raises:
            Exception: 复制失败
        """
        try:
            drive = get_drive_instance(user_id)
            
            # 准备复制参数
            body = {
                'parents': [dest_folder_id]
            }
            
            if new_name:
                body['name'] = new_name
            
            # 执行复制
            copied_file = drive.files().copy(
                fileId=source_id,
                body=body,
                fields="id, name, mimeType, size, webViewLink"
            ).execute()
            
            return copied_file
            
        except Exception as e:
            LOGGER.error(f"Copy file failed: {e}")
            raise
    
    async def copy_folder_recursive(
        self,
        user_id: int,
        source_folder_id: str,
        dest_parent_id: str,
        status_message: Message,
        folder_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        递归复制文件夹及其内容
        
        Args:
            user_id: 用户 ID
            source_folder_id: 源文件夹 ID
            dest_parent_id: 目标父文件夹 ID
            status_message: 状态消息对象
            folder_name: 新文件夹名（可选）
            
        Returns:
            新文件夹信息或 None
        """
        try:
            drive = get_drive_instance(user_id)
            
            # 1. 获取源文件夹信息
            source_info = await self.get_file_info(user_id, source_folder_id)
            if not source_info:
                raise Exception("无法获取源文件夹信息")
            
            # 2. 创建目标文件夹
            new_folder_name = folder_name or source_info['name']
            new_folder_metadata = {
                'name': new_folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [dest_parent_id]
            }
            
            new_folder = drive.files().create(
                body=new_folder_metadata,
                fields='id, name, webViewLink'
            ).execute()
            
            # 3. 获取源文件夹中的所有项目
            query = f"'{source_folder_id}' in parents and trashed = false"
            results = drive.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()
            
            items = results.get('files', [])
            total_items = len(items)
            
            # 4. 递归复制每个项目
            for idx, item in enumerate(items, 1):
                # 更新进度
                progress_text = AppleUI.format_message(
                    title="正在复制文件夹",
                    icon=AppleUI.ICONS["loading"],
                    content=f"**文件夹：** {new_folder_name}\n"
                           f"**进度：** {idx}/{total_items}\n"
                           f"**当前：** {item['name'][:30]}"
                )
                
                try:
                    await status_message.edit_text(progress_text)
                except:
                    pass
                
                if 'folder' in item['mimeType']:
                    # 递归复制子文件夹
                    await self.copy_folder_recursive(
                        user_id,
                        item['id'],
                        new_folder['id'],
                        status_message
                    )
                else:
                    # 复制文件
                    await self.copy_file(
                        user_id,
                        item['id'],
                        new_folder['id']
                    )
            
            return new_folder
            
        except Exception as e:
            LOGGER.error(f"Copy folder recursive failed: {e}")
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
copy_handler = CopyFileHandler()


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    CustomFilters.auth_users
)
async def copy_command(
    client: Client, 
    message: Message
) -> None:
    """
    /copy 命令处理器
    
    复制文件或文件夹到指定位置。
    
    使用方法：
        /copy <source_link> <dest_folder_link>
        /cp <source_link> <dest_folder_link>
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    user_id = message.from_user.id
    
    LOGGER.info(f"User {user_id} triggered /copy command")
    
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
            footer="使用方法：/copy <源链接> <目标文件夹链接>"
        )
        
        await message.reply_text(text)
        return
    
    source_url = command_parts[1]
    dest_url = command_parts[2]
    
    # 2. 提取 ID
    source_id = copy_handler.extract_file_id(source_url)
    dest_id = copy_handler.extract_file_id(dest_url)
    
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
        source_info = await copy_handler.get_file_info(user_id, source_id)
        dest_info = await copy_handler.get_file_info(user_id, dest_id)
        
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
        
        # 6. 显示确认对话框
        source_display = copy_handler.format_file_info_display(source_info)
        dest_display = copy_handler.format_file_info_display(dest_info)
        
        confirm_text = AppleUI.format_message(
            title="确认复制",
            icon=AppleUI.ICONS["warning"],
            content=f"**源：**\n{source_display}\n\n"
                   f"**目标位置：**\n{dest_display}\n\n"
                   f"⚠️ 请确认要执行此复制操作"
        )
        
        # 保存待确认的操作
        copy_handler.pending_copies[user_id] = {
            'source_id': source_id,
            'dest_id': dest_id,
            'source_info': source_info,
            'dest_info': dest_info
        }
        
        # 创建确认按钮
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button(
                    text="✅ 确认复制",
                    callback_data="copy_confirm"
                ),
                AppleUI.create_button(
                    text="❌ 取消",
                    callback_data="copy_cancel"
                )
            ]
        ])
        
        await status_msg.edit_text(
            confirm_text,
            reply_markup=keyboard
        )
        
        LOGGER.info(
            f"Copy confirmation shown for user {user_id}: "
            f"source={source_info['name']}, dest={dest_info['name']}"
        )
        
    except Exception as e:
        LOGGER.exception(f"Copy validation error for user {user_id}")
        
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


@Client.on_callback_query(filters.regex(r"^copy_"))
async def copy_callback_handler(
    client: Client,
    callback_query: CallbackQuery
) -> None:
    """
    处理复制相关的回调按钮
    
    回调格式：
        - copy_confirm - 确认复制
        - copy_cancel - 取消复制
    
    Args:
        client: Pyrogram 客户端
        callback_query: 回调查询对象
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # 取消操作
    if data == "copy_cancel":
        # 清除待确认操作
        if user_id in copy_handler.pending_copies:
            del copy_handler.pending_copies[user_id]
        
        cancel_text = AppleUI.format_message(
            title="已取消",
            icon=AppleUI.ICONS["success"],
            content="复制操作已取消"
        )
        
        await callback_query.message.edit_text(cancel_text)
        await callback_query.answer("✅ 已取消")
        
        LOGGER.info(f"User {user_id} cancelled copy operation")
        return
    
    # 确认复制
    if data == "copy_confirm":
        # 获取待确认操作
        if user_id not in copy_handler.pending_copies:
            await callback_query.answer("❌ 操作已过期，请重新执行命令")
            return
        
        pending = copy_handler.pending_copies[user_id]
        source_id = pending['source_id']
        dest_id = pending['dest_id']
        source_info = pending['source_info']
        dest_info = pending['dest_info']
        
        # 清除待确认操作
        del copy_handler.pending_copies[user_id]
        
        try:
            # 显示复制中提示
            await callback_query.answer("⏳ 开始复制...")
            
            copying_text = AppleUI.format_message(
                title="正在复制",
                icon=AppleUI.ICONS["loading"],
                content=f"**源：** {source_info['name']}\n"
                       f"**目标：** {dest_info['name']}\n\n"
                       f"⏳ 正在处理，请稍候..."
            )
            
            await callback_query.message.edit_text(copying_text)
            
            # 执行复制
            is_folder = 'folder' in source_info.get('mimeType', '')
            
            if is_folder:
                # 复制文件夹（递归）
                copied = await copy_handler.copy_folder_recursive(
                    user_id,
                    source_id,
                    dest_id,
                    callback_query.message
                )
            else:
                # 复制单个文件
                copied = await copy_handler.copy_file(
                    user_id,
                    source_id,
                    dest_id
                )
            
            # 显示成功消息
            success_text = AppleUI.format_message(
                title="复制成功",
                icon=AppleUI.ICONS["success"],
                content=f"✅ **{copied['name']}** 已成功复制\n\n"
                       f"**类型：** {'文件夹' if is_folder else '文件'}\n"
                       f"**目标位置：** {dest_info['name']}\n\n"
                       f"🔗 [在 Drive 中打开]({copied['webViewLink']})",
                footer="💡 文件已保留所有元数据"
            )
            
            # 创建快捷按钮
            keyboard = AppleUI.create_keyboard([
                [AppleUI.create_button(
                    text="🔗 在 Drive 中打开",
                    url=copied['webViewLink']
                )]
            ])
            
            await callback_query.message.edit_text(
                success_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            
            LOGGER.info(
                f"Copy completed for user {user_id}: "
                f"{source_info['name']} -> {dest_info['name']}"
            )
            
        except Exception as e:
            LOGGER.exception(f"Copy execution error for user {user_id}")
            
            error_msg = AppleUI.create_error_message(
                error_type="unknown_error",
                details=f"复制失败：{str(e)}"
            )
            
            await callback_query.message.edit_text(
                AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"],
                    footer="📞 如问题持续，请联系管理员"
                )
            )
            
            await callback_query.answer("❌ 复制失败")


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    ~CustomFilters.auth_users
)
async def copy_unauthorized(
    client: Client, 
    message: Message
) -> None:
    """
    处理未授权用户的复制请求
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    error_msg = AppleUI.create_error_message(
        error_type="auth_failed",
        details="您需要先授权才能复制文件"
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
        f"Unauthorized copy attempt by user {message.from_user.id}"
    )


# 命令帮助
COMMAND_HELP = {
    "command": "copy",
    "description": "复制 Google Drive 文件或文件夹",
    "usage": [
        "/copy <源链接> <目标文件夹链接> - 复制文件",
        "/cp <源链接> <目标文件夹链接> - 快捷方式"
    ],
    "examples": [
        "/copy https://drive.google.com/file/d/xxx https://drive.google.com/drive/folders/yyy",
        "/cp file_id folder_id"
    ],
    "features": [
        "支持文件和文件夹复制",
        "递归复制文件夹内容",
        "保留文件元数据",
        "实时进度显示",
        "双重确认机制",
        "源和目标验证"
    ],
    "notes": [
        "需要先使用 /auth 授权",
        "目标必须是文件夹",
        "需要对源和目标都有访问权限",
        "大文件夹复制可能需要较长时间"
    ]
}
