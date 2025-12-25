"""Drive 搜索基础版

此模块提供 /searchdrive 命令，作为 search_apple.py 的简化版本。
遵循 AGENTS.md 开发规范，使用 AppleUI 设计语言。

Author: AI Agent
Version: 1.0.0
Date: 2024-12-25
"""

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup
from typing import List, Dict, Optional
import logging

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
COMMAND_NAME = "searchdrive"
COMMAND_ALIASES = ["searchdrive", "sd"]


class SearchDriveHandler:
    """
    Drive 搜索基础版处理器
    
    提供简单的文件搜索功能，不包含高级特性。
    """
    
    def __init__(self):
        self.max_results = 10  # 基础版限制结果数
    
    async def search_files(
        self, 
        user_id: int, 
        query: str
    ) -> List[Dict[str, str]]:
        """
        搜索 Drive 文件
        
        Args:
            user_id: 用户 ID
            query: 搜索关键词
            
        Returns:
            文件列表
            
        Raises:
            Exception: 搜索失败
        """
        try:
            # 使用 get_drive_instance（遵循 AGENTS.md）
            drive = get_drive_instance(user_id)
            
            # 构建搜索查询
            search_query = f"name contains '{query}' and trashed = false"
            
            # 执行搜索
            results = drive.files().list(
                q=search_query,
                pageSize=self.max_results,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            LOGGER.error(f"Search failed for user {user_id}: {e}")
            raise
    
    def format_file_info(self, file: Dict) -> str:
        """
        格式化文件信息
        
        Args:
            file: 文件对象
            
        Returns:
            格式化的文本
        """
        # 确定文件类型图标
        mime_type = file.get('mimeType', '')
        if 'folder' in mime_type:
            icon = AppleUI.ICONS['folder']
        elif 'document' in mime_type:
            icon = AppleUI.ICONS['document']
        elif 'video' in mime_type:
            icon = AppleUI.ICONS['video']
        elif 'image' in mime_type:
            icon = AppleUI.ICONS['image']
        else:
            icon = AppleUI.ICONS['file']
        
        # 文件名
        name = file.get('name', 'Unknown')
        
        # 文件大小
        size = file.get('size')
        size_str = self._format_size(int(size)) if size else 'N/A'
        
        # 修改日期
        modified = file.get('modifiedTime', '')[:10]  # YYYY-MM-DD
        
        # 构建信息文本
        info = f"{icon} **{name}**\n"
        info += f"   • 大小：{size_str}\n"
        info += f"   • 修改：{modified}"
        
        return info
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def create_file_buttons(self, files: List[Dict]) -> InlineKeyboardMarkup:
        """
        创建文件操作按钮
        
        Args:
            files: 文件列表
            
        Returns:
            按钮键盘
        """
        buttons = []
        
        for file in files:
            # 每个文件一行，显示“打开”按钮
            file_id = file.get('id')
            file_name = file.get('name', 'Unknown')[:30]  # 限制长度
            
            button = AppleUI.create_button(
                text=f"🔗 {file_name}",
                callback_data=f"open_file:{file_id}",
                url=file.get('webViewLink')
            )
            buttons.append([button])
        
        return AppleUI.create_keyboard(buttons) if buttons else None


# 全局处理器实例
search_handler = SearchDriveHandler()


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    CustomFilters.auth_users  # 需要授权
)
async def searchdrive_command(
    client: Client, 
    message: Message
) -> None:
    """
    /searchdrive 命令处理器
    
    基础版本的 Drive 文件搜索功能。
    
    使用方法：
        /searchdrive <关键词>
        /sd <关键词>
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    user_id = message.from_user.id
    
    # 记录日志
    LOGGER.info(
        f"User {user_id} triggered /searchdrive command"
    )
    
    # 1. 检查输入
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        # 输入验证失败
        error_msg = AppleUI.create_error_message(
            error_type="invalid_input",
            details="请提供搜索关键词"
        )
        
        text = AppleUI.format_message(
            title=error_msg["title"],
            icon=error_msg["icon"],
            content=error_msg["message"],
            footer="使用方法：/searchdrive <关键词>"
        )
        
        await message.reply_text(text)
        return
    
    query = command_parts[1].strip()
    
    # 2. 发送搜索中提示
    searching_text = AppleUI.format_message(
        title="正在搜索",
        icon=AppleUI.ICONS["search"],
        content=f"搜索关键词：**{query}**\n\n请稍候..."
    )
    
    status_msg = await message.reply_text(searching_text)
    
    try:
        # 3. 执行搜索
        files = await search_handler.search_files(user_id, query)
        
        # 4. 处理结果
        if not files:
            # 未找到结果
            no_results = AppleUI.format_message(
                title="未找到结果",
                icon=AppleUI.ICONS["warning"],
                content=f"搜索 **{query}** 未找到任何文件。\n\n"
                       f"💡 尝试：\n"
                       f"• 使用更通用的关键词\n"
                       f"• 检查拼写是否正确\n"
                       f"• 尝试使用部分匹配"
            )
            
            await status_msg.edit_text(no_results)
            return
        
        # 5. 格式化结果
        result_count = len(files)
        result_text = f"找到 **{result_count}** 个结果：\n\n"
        
        for i, file in enumerate(files, 1):
            result_text += f"**{i}.** "
            result_text += search_handler.format_file_info(file)
            result_text += "\n\n"
        
        # 6. 创建成功消息
        success_text = AppleUI.format_message(
            title="搜索完成",
            icon=AppleUI.ICONS["success"],
            content=result_text,
            footer=f"🔍 搜索关键词：{query}"
        )
        
        # 7. 创建按钮
        keyboard = search_handler.create_file_buttons(files)
        
        # 8. 发送结果
        await status_msg.edit_text(
            success_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        LOGGER.info(
            f"Search completed for user {user_id}: "
            f"{result_count} results found"
        )
        
    except Exception as e:
        # 9. 错误处理
        LOGGER.exception(f"Search error for user {user_id}")
        
        # 判断错误类型
        if "credentials" in str(e).lower():
            error_type = "auth_failed"
            details = "请先使用 /auth 进行授权"
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_type = "network_error"
            details = "请检查网络连接"
        elif "permission" in str(e).lower():
            error_type = "permission_denied"
            details = "请检查 Drive 权限"
        else:
            error_type = "unknown_error"
            details = str(e)
        
        error_msg = AppleUI.create_error_message(
            error_type=error_type,
            details=details
        )
        
        error_text = AppleUI.format_message(
            title=error_msg["title"],
            icon=error_msg["icon"],
            content=error_msg["message"],
            footer="📞 如问题持续，请联系管理员"
        )
        
        await status_msg.edit_text(error_text)


@Client.on_message(
    filters.command(["searchdrive", "sd"]) & 
    filters.private & 
    ~CustomFilters.auth_users  # 未授权用户
)
async def searchdrive_unauthorized(
    client: Client, 
    message: Message
) -> None:
    """
    处理未授权用户的搜索请求
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    error_msg = AppleUI.create_error_message(
        error_type="auth_failed",
        details="您需要先授权才能使用搜索功能"
    )
    
    text = AppleUI.format_message(
        title=error_msg["title"],
        icon=error_msg["icon"],
        content=error_msg["message"],
        footer="🔑 使用 /auth 开始授权"
    )
    
    # 添加授权按钮
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            text="🔑 立即授权",
            callback_data="start_auth"
        )]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)
    
    LOGGER.warning(
        f"Unauthorized search attempt by user {message.from_user.id}"
    )


# 命令帮助（用于 /help）
COMMAND_HELP = {
    "command": "searchdrive",
    "description": "搜索 Google Drive 文件",
    "usage": [
        "/searchdrive <关键词> - 搜索文件",
        "/sd <关键词> - 快捷方式"
    ],
    "examples": [
        "/searchdrive 项目文档",
        "/sd report.pdf",
        "/searchdrive 照片"
    ],
    "notes": [
        "需要先使用 /auth 授权",
        "每次最多显示 10 个结果",
        "支持模糊匹配"
    ]
}
