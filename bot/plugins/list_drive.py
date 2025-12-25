"""Drive 文件列表功能

提供完整的 Drive 文件浏览系统，支持分页、导航和递归浏览。
遵循 AGENTS.md 开发规范，使用 AppleUI 设计语言。

Author: AI Agent
Version: 1.0.0
Date: 2024-12-25
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from typing import List, Dict, Optional, Tuple
import logging
import re
from urllib.parse import urlparse, parse_qs

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
COMMAND_NAME = "list"
COMMAND_ALIASES = ["list", "ls"]

# 配置
ITEMS_PER_PAGE = 10  # 每页显示项数
MAX_RECURSIVE_ITEMS = 100  # 递归模式最大项数


class DriveListHandler:
    """
    Drive 文件列表处理器
    
    提供文件和文件夹的浏览、导航和分页功能。
    """
    
    def __init__(self):
        # 存储用户当前浏览位置
        self.user_navigation = {}  # {user_id: {folder_id, page, path}}
    
    def extract_folder_id(self, url: str) -> Optional[str]:
        """
        从 Google Drive URL 提取文件夹 ID
        
        Args:
            url: Drive URL
            
        Returns:
            文件夹 ID 或 None
        """
        try:
            # 支持多种 URL 格式
            patterns = [
                r'folders/([a-zA-Z0-9-_]+)',
                r'id=([a-zA-Z0-9-_]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            LOGGER.error(f"Error extracting folder ID: {e}")
            return None
    
    async def list_files(
        self, 
        user_id: int,
        folder_id: Optional[str] = None,
        page: int = 1,
        recursive: bool = False
    ) -> Tuple[List[Dict], int]:
        """
        列出文件和文件夹
        
        Args:
            user_id: 用户 ID
            folder_id: 文件夹 ID（None 表示根目录）
            page: 页码
            recursive: 是否递归列出
            
        Returns:
            (文件列表, 总数)
            
        Raises:
            Exception: 列表失败
        """
        try:
            drive = get_drive_instance(user_id)
            
            # 构建查询
            if folder_id:
                query = f"'{folder_id}' in parents and trashed = false"
            else:
                # 根目录：My Drive
                query = "'root' in parents and trashed = false"
            
            if recursive:
                # 递归模式：获取所有文件
                results = drive.files().list(
                    q="trashed = false",
                    pageSize=MAX_RECURSIVE_ITEMS,
                    fields="files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                    orderBy="folder,name"
                ).execute()
            else:
                # 分页模式
                results = drive.files().list(
                    q=query,
                    pageSize=ITEMS_PER_PAGE * 2,  # 获取两页数据以判断是否有下一页
                    fields="files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                    orderBy="folder,name"
                ).execute()
            
            files = results.get('files', [])
            total_count = len(files)
            
            # 分页
            if not recursive:
                start_idx = (page - 1) * ITEMS_PER_PAGE
                end_idx = start_idx + ITEMS_PER_PAGE
                files = files[start_idx:end_idx]
            
            return files, total_count
            
        except Exception as e:
            LOGGER.error(f"List files failed for user {user_id}: {e}")
            raise
    
    async def get_folder_path(
        self, 
        user_id: int,
        folder_id: str
    ) -> List[Dict[str, str]]:
        """
        获取文件夹路径（面包屑导航）
        
        Args:
            user_id: 用户 ID
            folder_id: 当前文件夹 ID
            
        Returns:
            路径列表 [{id, name}]
        """
        try:
            drive = get_drive_instance(user_id)
            path = []
            current_id = folder_id
            
            # 向上遍历最多5层
            for _ in range(5):
                if not current_id or current_id == 'root':
                    break
                
                try:
                    folder = drive.files().get(
                        fileId=current_id,
                        fields="id, name, parents"
                    ).execute()
                    
                    path.insert(0, {
                        'id': folder['id'],
                        'name': folder['name']
                    })
                    
                    # 获取父文件夹
                    parents = folder.get('parents', [])
                    current_id = parents[0] if parents else None
                    
                except:
                    break
            
            # 添加根目录
            path.insert(0, {'id': 'root', 'name': '🏠 My Drive'})
            
            return path
            
        except Exception as e:
            LOGGER.error(f"Get folder path failed: {e}")
            return [{'id': 'root', 'name': '🏠 My Drive'}]
    
    def format_file_item(
        self, 
        file: Dict,
        index: int
    ) -> str:
        """
        格式化单个文件/文件夹项
        
        Args:
            file: 文件对象
            index: 序号
            
        Returns:
            格式化的文本
        """
        # 确定图标
        mime_type = file.get('mimeType', '')
        if 'folder' in mime_type:
            icon = AppleUI.ICONS['folder']
            type_str = "文件夹"
        elif 'document' in mime_type:
            icon = AppleUI.ICONS['document']
            type_str = "文档"
        elif 'video' in mime_type:
            icon = AppleUI.ICONS['video']
            type_str = "视频"
        elif 'image' in mime_type:
            icon = AppleUI.ICONS['image']
            type_str = "图片"
        elif 'audio' in mime_type:
            icon = "🎵"
            type_str = "音频"
        elif 'pdf' in mime_type:
            icon = "📕"
            type_str = "PDF"
        elif 'zip' in mime_type or 'compressed' in mime_type:
            icon = "📦"
            type_str = "压缩包"
        else:
            icon = AppleUI.ICONS['file']
            type_str = "文件"
        
        # 文件名（限制长度）
        name = file.get('name', 'Unknown')
        if len(name) > 30:
            name = name[:27] + "..."
        
        # 文件大小
        size = file.get('size')
        if size and 'folder' not in mime_type:
            size_str = self._format_size(int(size))
        else:
            size_str = "-"
        
        # 修改日期
        modified = file.get('modifiedTime', '')[:10]
        
        # 格式化输出
        item_text = f"{icon} **{name}**"
        if 'folder' not in mime_type:
            item_text += f"\n   📊 {size_str} • 📅 {modified}"
        
        return item_text
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def create_navigation_keyboard(
        self,
        files: List[Dict],
        current_page: int,
        total_count: int,
        folder_id: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """
        创建导航键盘
        
        Args:
            files: 文件列表
            current_page: 当前页码
            total_count: 总项数
            folder_id: 当前文件夹 ID
            parent_id: 父文件夹 ID
            
        Returns:
            键盘布局
        """
        buttons = []
        
        # 文件夹按钮（可进入）
        for file in files:
            if 'folder' in file.get('mimeType', ''):
                file_id = file['id']
                file_name = file['name'][:20]
                buttons.append([AppleUI.create_button(
                    text=f"📁 {file_name}",
                    callback_data=f"list_enter:{file_id}:1"
                )])
        
        # 分页按钮
        total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        if total_pages > 1:
            page_buttons = []
            
            # 上一页
            if current_page > 1:
                page_buttons.append(AppleUI.create_button(
                    text="⬅️ 上一页",
                    callback_data=f"list_page:{folder_id or 'root'}:{current_page-1}"
                ))
            
            # 页码指示
            page_buttons.append(AppleUI.create_button(
                text=f"📄 {current_page}/{total_pages}",
                callback_data="list_noop"
            ))
            
            # 下一页
            if current_page < total_pages:
                page_buttons.append(AppleUI.create_button(
                    text="➡️ 下一页",
                    callback_data=f"list_page:{folder_id or 'root'}:{current_page+1}"
                ))
            
            buttons.append(page_buttons)
        
        # 返回上级按钮
        if folder_id and folder_id != 'root':
            buttons.append([AppleUI.create_button(
                text="🔙 返回上级",
                callback_data=f"list_back:{parent_id or 'root'}:1"
            )])
        
        # 刷新按钮
        buttons.append([AppleUI.create_button(
            text="🔄 刷新",
            callback_data=f"list_refresh:{folder_id or 'root'}:{current_page}"
        )])
        
        return AppleUI.create_keyboard(buttons) if buttons else None


# 全局处理器实例
list_handler = DriveListHandler()


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    CustomFilters.auth_users
)
async def list_command(
    client: Client, 
    message: Message
) -> None:
    """
    /list 命令处理器
    
    列出 Drive 文件和文件夹。
    
    使用方法：
        /list - 列出根目录
        /list <folder_link> - 列出指定文件夹
        /list -r - 递归列出所有文件
        /ls - 快捷方式
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    user_id = message.from_user.id
    
    LOGGER.info(f"User {user_id} triggered /list command")
    
    # 解析参数
    command_parts = message.text.split(maxsplit=1)
    folder_id = None
    recursive = False
    
    if len(command_parts) > 1:
        arg = command_parts[1].strip()
        
        # 检查是否递归模式
        if arg == '-r':
            recursive = True
        else:
            # 尝试提取文件夹 ID
            folder_id = list_handler.extract_folder_id(arg)
            
            if not folder_id:
                error_msg = AppleUI.create_error_message(
                    error_type="invalid_input",
                    details="无效的文件夹链接"
                )
                
                text = AppleUI.format_message(
                    title=error_msg["title"],
                    icon=error_msg["icon"],
                    content=error_msg["message"],
                    footer="使用方法：/list 或 /list <folder_link>"
                )
                
                await message.reply_text(text)
                return
    
    # 发送加载中提示
    loading_text = AppleUI.format_message(
        title="正在加载",
        icon=AppleUI.ICONS["loading"],
        content="正在获取文件列表...\n\n请稍候"
    )
    
    status_msg = await message.reply_text(loading_text)
    
    try:
        # 获取文件列表
        files, total_count = await list_handler.list_files(
            user_id=user_id,
            folder_id=folder_id,
            page=1,
            recursive=recursive
        )
        
        if not files:
            # 空文件夹
            empty_text = AppleUI.format_message(
                title="文件夹为空",
                icon=AppleUI.ICONS["warning"],
                content="这个文件夹中没有任何文件或子文件夹。\n\n"
                       "💡 提示：\n"
                       "• 上传文件到 Drive\n"
                       "• 检查文件夹权限\n"
                       "• 刷新重试"
            )
            
            await status_msg.edit_text(empty_text)
            return
        
        # 获取文件夹路径（面包屑）
        if folder_id:
            path = await list_handler.get_folder_path(user_id, folder_id)
            breadcrumb = " > ".join([p['name'] for p in path])
        else:
            breadcrumb = "🏠 My Drive"
        
        # 格式化文件列表
        file_list = ""
        for i, file in enumerate(files, 1):
            file_list += f"**{i}.** "
            file_list += list_handler.format_file_item(file, i)
            file_list += "\n\n"
        
        # 构建消息
        if recursive:
            title = "📂 递归列表"
            footer = f"总计 {total_count} 项（限制 {MAX_RECURSIVE_ITEMS}）"
        else:
            total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            title = "📂 文件列表"
            footer = f"第 1/{total_pages} 页 • 共 {total_count} 项"
        
        list_text = AppleUI.format_message(
            title=title,
            icon=AppleUI.ICONS["folder"],
            content=f"**📍 位置：** {breadcrumb}\n\n{file_list}",
            footer=footer
        )
        
        # 创建导航键盘（仅非递归模式）
        keyboard = None
        if not recursive:
            # 获取父文件夹 ID
            parent_id = None
            if files and files[0].get('parents'):
                parent_id = files[0]['parents'][0]
            
            keyboard = list_handler.create_navigation_keyboard(
                files=files,
                current_page=1,
                total_count=total_count,
                folder_id=folder_id,
                parent_id=parent_id
            )
        
        # 发送结果
        await status_msg.edit_text(
            list_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        LOGGER.info(
            f"List completed for user {user_id}: "
            f"{total_count} items found"
        )
        
    except Exception as e:
        LOGGER.exception(f"List error for user {user_id}")
        
        # 判断错误类型
        if "credentials" in str(e).lower():
            error_type = "auth_failed"
            details = "请先使用 /auth 进行授权"
        elif "not found" in str(e).lower():
            error_type = "file_not_found"
            details = "文件夹不存在或已删除"
        elif "permission" in str(e).lower():
            error_type = "permission_denied"
            details = "您没有访问此文件夹的权限"
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


@Client.on_callback_query(filters.regex(r"^list_"))
async def list_callback_handler(
    client: Client,
    callback_query: CallbackQuery
) -> None:
    """
    处理列表相关的回调按钮
    
    回调格式：
        - list_enter:<folder_id>:<page> - 进入文件夹
        - list_page:<folder_id>:<page> - 翻页
        - list_back:<parent_id>:<page> - 返回上级
        - list_refresh:<folder_id>:<page> - 刷新
        - list_noop - 无操作
    
    Args:
        client: Pyrogram 客户端
        callback_query: 回调查询对象
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # 无操作
    if data == "list_noop":
        await callback_query.answer("📄 页码指示")
        return
    
    # 解析回调数据
    parts = data.split(":")
    if len(parts) < 3:
        await callback_query.answer("❌ 无效的操作")
        return
    
    action = parts[0].replace("list_", "")
    folder_id = parts[1] if parts[1] != 'root' else None
    page = int(parts[2])
    
    try:
        # 显示加载动画
        await callback_query.answer("⏳ 加载中...")
        
        # 获取文件列表
        files, total_count = await list_handler.list_files(
            user_id=user_id,
            folder_id=folder_id,
            page=page,
            recursive=False
        )
        
        if not files:
            await callback_query.answer("📭 文件夹为空")
            return
        
        # 获取路径
        if folder_id:
            path = await list_handler.get_folder_path(user_id, folder_id)
            breadcrumb = " > ".join([p['name'] for p in path])
        else:
            breadcrumb = "🏠 My Drive"
        
        # 格式化列表
        file_list = ""
        for i, file in enumerate(files, 1):
            file_list += f"**{i}.** "
            file_list += list_handler.format_file_item(file, i)
            file_list += "\n\n"
        
        # 构建消息
        total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        list_text = AppleUI.format_message(
            title="📂 文件列表",
            icon=AppleUI.ICONS["folder"],
            content=f"**📍 位置：** {breadcrumb}\n\n{file_list}",
            footer=f"第 {page}/{total_pages} 页 • 共 {total_count} 项"
        )
        
        # 创建键盘
        parent_id = None
        if files and files[0].get('parents'):
            parent_id = files[0]['parents'][0]
        
        keyboard = list_handler.create_navigation_keyboard(
            files=files,
            current_page=page,
            total_count=total_count,
            folder_id=folder_id,
            parent_id=parent_id
        )
        
        # 更新消息
        await callback_query.message.edit_text(
            list_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        LOGGER.info(
            f"User {user_id} navigated: action={action}, "
            f"folder={folder_id}, page={page}"
        )
        
    except Exception as e:
        LOGGER.exception(f"Callback error for user {user_id}")
        await callback_query.answer(f"❌ 操作失败: {str(e)[:50]}")


@Client.on_message(
    filters.command(COMMAND_ALIASES) & 
    filters.private & 
    ~CustomFilters.auth_users
)
async def list_unauthorized(
    client: Client, 
    message: Message
) -> None:
    """
    处理未授权用户的列表请求
    
    Args:
        client: Pyrogram 客户端
        message: 消息对象
    """
    error_msg = AppleUI.create_error_message(
        error_type="auth_failed",
        details="您需要先授权才能浏览文件"
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
        f"Unauthorized list attempt by user {message.from_user.id}"
    )


# 命令帮助
COMMAND_HELP = {
    "command": "list",
    "description": "列出 Google Drive 文件和文件夹",
    "usage": [
        "/list - 列出根目录文件",
        "/list <folder_link> - 列出指定文件夹",
        "/list -r - 递归列出所有文件",
        "/ls - 快捷方式"
    ],
    "examples": [
        "/list",
        "/list https://drive.google.com/drive/folders/xxx",
        "/list -r",
        "/ls"
    ],
    "features": [
        "分页浏览（每页10项）",
        "文件夹导航",
        "面包屑路径显示",
        "递归模式（最多100项）",
        "文件类型图标",
        "文件大小和日期"
    ],
    "notes": [
        "需要先使用 /auth 授权",
        "点击文件夹按钮可进入",
        "使用导航按钮翻页和返回",
        "递归模式显示所有文件但不支持导航"
    ]
}
