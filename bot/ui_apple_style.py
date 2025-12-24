"""
Apple 设计风格 UI 工具模块
提供统一的消息格式、按钮样式和交互设计
遵循 Apple Human Interface Guidelines
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AppleUI:
    """Apple 风格 UI 组件工具类"""

    # Emoji 图标系统（模拟 SF Symbols）
    ICONS = {
        # 主要功能图标
        "upload": "📤",
        "download": "📥",
        "folder": "📁",
        "file": "📄",
        "settings": "⚙️",
        "help": "❓",
        "info": "ℹ️",
        
        # 状态图标
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "processing": "⏳",
        "completed": "✓",
        
        # 操作图标
        "play": "▶️",
        "pause": "⏸",
        "stop": "⏹",
        "cancel": "✕",
        "refresh": "🔄",
        "search": "🔍",
        "delete": "🗑",
        "copy": "📋",
        
        # 导航图标
        "back": "◀️",
        "forward": "▶️",
        "home": "🏠",
        "menu": "☰",
        
        # Google Drive 相关
        "gdrive": "☁️",
        "auth": "🔐",
        "link": "🔗",
        
        # 进度和状态
        "downloading": "⬇️",
        "uploading": "⬆️",
        "mirroring": "🔄",
    }

    @staticmethod
    def format_title(text: str) -> str:
        """格式化标题（粗体）"""
        return f"**{text}**"

    @staticmethod
    def format_subtitle(text: str) -> str:
        """格式化副标题（斜体）"""
        return f"__{text}__"

    @staticmethod
    def format_code(text: str) -> str:
        """格式化代码（等宽字体）"""
        return f"`{text}`"

    @staticmethod
    def format_message(
        title: str = "",
        subtitle: str = "",
        content: str = "",
        footer: str = "",
        icon: str = ""
    ) -> str:
        """
        Apple 风格的消息格式化
        
        Args:
            title: 主标题
            subtitle: 副标题
            content: 内容主体
            footer: 页脚信息
            icon: 标题前的图标
            
        Returns:
            格式化后的消息文本
        """
        parts = []
        
        # 标题
        if title:
            title_text = f"{icon} {title}" if icon else title
            parts.append(f"**{title_text}**\n")
        
        # 副标题
        if subtitle:
            parts.append(f"__{subtitle}__\n")
        
        # 内容主体
        if content:
            parts.append(f"{content}\n")
        
        # 页脚
        if footer:
            parts.append(f"\n{footer}")
        
        return "\n".join(parts).strip()

    @staticmethod
    def create_button(
        text: str,
        callback_data: str = None,
        url: str = None,
        icon: str = ""
    ) -> InlineKeyboardButton:
        """
        创建 Apple 风格按钮
        
        Args:
            text: 按钮文本
            callback_data: 回调数据
            url: URL 链接
            icon: 按钮前的图标
            
        Returns:
            InlineKeyboardButton 对象
        """
        button_text = f"{icon}  {text}" if icon else text
        
        if url:
            return InlineKeyboardButton(button_text, url=url)
        else:
            return InlineKeyboardButton(button_text, callback_data=callback_data)

    @staticmethod
    def create_keyboard(
        buttons: list,
        row_width: int = 2
    ) -> InlineKeyboardMarkup:
        """
        创建 Apple 风格键盘布局
        
        Args:
            buttons: 按钮列表，可以是嵌套列表来指定行
            row_width: 每行按钮数量（当 buttons 为一维列表时）
            
        Returns:
            InlineKeyboardMarkup 对象
        """
        # 如果已经是嵌套列表（已指定行），直接使用
        if buttons and isinstance(buttons[0], list):
            return InlineKeyboardMarkup(buttons)
        
        # 否则按 row_width 分组
        keyboard = []
        for i in range(0, len(buttons), row_width):
            keyboard.append(buttons[i:i + row_width])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def format_progress(
        current: int,
        total: int,
        status: str = "uploading",
        filename: str = "",
        speed: str = ""
    ) -> str:
        """
        Apple 风格的进度显示
        
        Args:
            current: 当前进度（字节）
            total: 总大小（字节）
            status: 状态类型
            filename: 文件名
            speed: 速度信息
            
        Returns:
            格式化的进度文本
        """
        percentage = (current / total * 100) if total > 0 else 0
        
        # 进度条（10 个字符）
        bar_length = 10
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # 状态图标
        status_icons = {
            "downloading": AppleUI.ICONS["downloading"],
            "uploading": AppleUI.ICONS["uploading"],
            "processing": AppleUI.ICONS["processing"],
            "completed": AppleUI.ICONS["completed"],
            "mirroring": AppleUI.ICONS["mirroring"],
        }
        icon = status_icons.get(status, AppleUI.ICONS["processing"])
        
        # 格式化大小
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        # 构建进度信息
        parts = [f"{icon} **{status.title()}**\n"]
        
        if filename:
            parts.append(f"`{filename}`\n")
        
        parts.append(f"{bar} {percentage:.1f}%\n")
        parts.append(f"{current_mb:.1f} MB / {total_mb:.1f} MB")
        
        if speed:
            parts.append(f" • {speed}")
        
        return "\n".join(parts)

    @staticmethod
    def format_list(
        items: list,
        title: str = "",
        icon: str = "•"
    ) -> str:
        """
        格式化列表
        
        Args:
            items: 列表项
            title: 列表标题
            icon: 列表项图标
            
        Returns:
            格式化的列表文本
        """
        parts = []
        
        if title:
            parts.append(f"**{title}**\n")
        
        for item in items:
            parts.append(f"{icon} {item}")
        
        return "\n".join(parts)

    @staticmethod
    def create_error_message(
        error_type: str,
        custom_message: str = None
    ) -> dict:
        """
        创建标准化的错误消息
        
        Args:
            error_type: 错误类型
            custom_message: 自定义错误消息
            
        Returns:
            包含 title, message, action 的字典
        """
        error_templates = {
            "auth_failed": {
                "title": f"{AppleUI.ICONS['error']} 认证失败",
                "message": "无法连接到 Google Drive\n\n请检查您的授权设置",
                "action": "重新授权"
            },
            "file_too_large": {
                "title": f"{AppleUI.ICONS['warning']} 文件过大",
                "message": "文件大小超过限制\n\n请选择较小的文件",
                "action": "了解更多"
            },
            "network_error": {
                "title": f"{AppleUI.ICONS['error']} 网络错误",
                "message": "连接中断，操作已暂停\n\n将在网络恢复后继续",
                "action": "重试"
            },
            "invalid_input": {
                "title": f"{AppleUI.ICONS['warning']} 无效输入",
                "message": custom_message or "输入格式不正确\n\n请检查后重试",
                "action": "查看帮助"
            },
            "permission_denied": {
                "title": f"{AppleUI.ICONS['error']} 权限不足",
                "message": "您没有权限执行此操作\n\n请联系管理员",
                "action": "了解更多"
            },
            "not_found": {
                "title": f"{AppleUI.ICONS['error']} 未找到",
                "message": custom_message or "未找到请求的资源\n\n请确认后重试",
                "action": "返回"
            }
        }
        
        return error_templates.get(error_type, {
            "title": f"{AppleUI.ICONS['error']} 错误",
            "message": custom_message or "发生未知错误",
            "action": "确定"
        })

    @staticmethod
    def create_success_message(
        title: str,
        message: str,
        action: str = "完成"
    ) -> dict:
        """
        创建成功消息
        
        Args:
            title: 成功标题
            message: 成功消息
            action: 操作按钮文本
            
        Returns:
            包含 title, message, action 的字典
        """
        return {
            "title": f"{AppleUI.ICONS['success']} {title}",
            "message": message,
            "action": action
        }


# 便捷函数
def create_welcome_message() -> tuple:
    """
    创建欢迎消息
    
    Returns:
        (消息文本, 键盘布局) 元组
    """
    text = AppleUI.format_message(
        title="Google Drive Uploader",
        subtitle="轻松上传文件到 Google Drive",
        content=(
            "__主要功能__\n"
            "• 上传 Telegram 文件\n"
            "• 支持直链下载\n"
            "• 团队盘支持\n"
            "• 文件镜像管理\n\n"
            "点击下方按钮开始使用"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("开始上传", callback_data="upload", icon=AppleUI.ICONS["upload"])],
        [
            AppleUI.create_button("设置", callback_data="settings", icon=AppleUI.ICONS["settings"]),
            AppleUI.create_button("帮助", callback_data="help", icon=AppleUI.ICONS["help"])
        ]
    ])
    
    return text, keyboard


def create_help_message() -> str:
    """
    创建帮助消息
    
    Returns:
        帮助文本
    """
    commands = [
        ("/start", "显示欢迎消息"),
        ("/help", "显示帮助信息"),
        ("/auth", "Google Drive 授权"),
        ("/revoke", "撤销授权"),
        ("/setfolder", "设置上传文件夹"),
        ("/mirror <链接>", "镜像文件到 Drive"),
        ("/clone <Drive链接>", "克隆 Drive 文件"),
        ("/delete <Drive链接>", "删除 Drive 文件"),
        ("/searchdrive <关键词>", "搜索 Drive 文件"),
        ("/listdrive", "列出 Drive 文件"),
    ]
    
    cmd_list = "\n".join([f"`{cmd}` - {desc}" for cmd, desc in commands])
    
    return AppleUI.format_message(
        title="命令帮助",
        icon=AppleUI.ICONS["help"],
        content=cmd_list,
        footer="💡 提示：点击命令可快速复制"
    )
