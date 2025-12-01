from enum import Enum


class MessageLevel(Enum):
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    LOADING = "⏳"
    QUESTION = "❓"


EMOJI_MAP = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "download": "📥",
    "upload": "📤",
    "file": "📄",
    "folder": "📁",
    "link": "🔗",
    "lock": "🔐",
    "unlock": "🔓",
    "key": "🔑",
    "search": "🔍",
    "list": "📋",
    "monitor": "📡",
    "delete": "🗑️",
    "trash": "🗑️",
    "copy": "📋",
    "clock": "⏰",
    "user": "👤",
    "robot": "🤖",
    "cloud": "☁️",
    "gear": "⚙️",
}


class MessageTemplate:
    @staticmethod
    def format_success(title: str, content: str = "", extra: str = "") -> str:
        msg = f"{EMOJI_MAP['success']} **{title}**"
        if content:
            msg += f"\n{content}"
        if extra:
            msg += f"\n{extra}"
        return msg

    @staticmethod
    def format_error(title: str, reason: str = "", suggestion: str = "") -> str:
        msg = f"{EMOJI_MAP['error']} **{title}**"
        if reason:
            msg += f"\n💡 原因：{reason}"
        if suggestion:
            msg += f"\n💬 建议：{suggestion}"
        return msg

    @staticmethod
    def format_warning(title: str, content: str = "", action: str = "") -> str:
        msg = f"{EMOJI_MAP['warning']} **{title}**"
        if content:
            msg += f"\n{content}"
        if action:
            msg += f"\n▶️ {action}"
        return msg

    @staticmethod
    def format_loading(title: str, details: str = "") -> str:
        msg = f"{EMOJI_MAP['loading']} **{title}**"
        if details:
            msg += f"\n{details}"
        return msg


def render_permission_error(resource: str = "此功能", action: str = "使用") -> str:
    return MessageTemplate.format_error(
        "权限不足",
        f"您没有权限{action}{resource}",
        "请联系管理员或确保您已正确授权",
    )
