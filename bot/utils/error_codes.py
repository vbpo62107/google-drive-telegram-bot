from enum import Enum


class ErrorCode(Enum):
    PERMISSION_DENIED = ("PERM_001", "权限不足", "您没有权限执行此操作")
    NOT_AUTHORIZED = ("AUTH_001", "未授权", "您需要先进行授权")
    NOT_SUDO_USER = ("AUTH_002", "非管理员", "仅管理员可使用此命令")
    INVALID_URL = ("FMT_001", "URL 无效", "请提供有效的 URL")
    FILE_NOT_FOUND = ("FILE_001", "文件不存在", "请检查文件是否存在")
    NETWORK_ERROR = ("NET_001", "网络错误", "请检查网络连接后重试")
    UNKNOWN_ERROR = ("ERR_999", "未知错误", "发生了未知错误，请联系管理员")


ERROR_DETAILS = {
    code.value[0]: {"title": code.value[1], "reason": code.value[2]} for code in ErrorCode
}


def get_error_message(error_code: str, context: str = "") -> str:
    if error_code not in ERROR_DETAILS:
        error_code = "ERR_999"
    detail = ERROR_DETAILS[error_code]
    msg = f"❌ **{detail['title']}**\n💡 原因：{detail['reason']}"
    if context:
        msg += f"\n📍 详情：{context}"
    return msg


def get_error_code_by_exception(exc: Exception) -> str:
    exc_type = type(exc).__name__
    exception_map = {
        "PermissionError": "PERM_001",
        "FileNotFoundError": "FILE_001",
        "TimeoutError": "NET_001",
        "ConnectionError": "NET_001",
    }
    return exception_map.get(exc_type, "ERR_999")
