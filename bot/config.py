class config:
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    APP_ID = "123456"
    API_HASH = "YOUR_API_HASH"
    DATABASE_URL = "postgres://username:password@host:5432/database"
    SUDO_USERS = "123456789"  # Space separated Telegram user IDs.
    SUPPORT_CHAT_LINK = "https://your-support-link"
    DOWNLOAD_DIRECTORY = "./downloads/"
    G_DRIVE_CLIENT_ID = "your-google-client-id"
    G_DRIVE_CLIENT_SECRET = "your-google-client-secret"
    MAX_MIRROR_FILE_SIZE = 10 * 1024 * 1024 * 1024
    MAX_CONCURRENT_MIRRORS = 2


class BotCommands:
    Download = ['download', 'dl']
    Authorize = ['auth', 'authorize']
    AuthMode = ['authmode']
    SetFolder = ['setfolder', 'setfl']
    Revoke = ['revoke']
    Clone = ['copy', 'clone']
    Delete = ['delete', 'del']
    EmptyTrash = ['emptytrash', 'emptyTrash']
    YtDl = ['ytdl']
    ListDrive = ['listdrive', 'lsdrive', 'listdriv']
    SearchDrive = ['searchdrive', 'sdrive']


# 替换原有的 class Messages: 块
class Messages:
    """改进版的消息常量类"""
    
    START_MSG = "👋 **欢迎使用 Google Drive 上传器**\n\n🤖 我是一个专业的文件上传助手，可以帮你：\n  • 📥 从直链下载文件到服务器\n  • 📤 自动上传到你的 Google Drive\n  • 🎬 支持 YouTube 视频下载\n  • 📡 自动监听频道并捕获文件\n\n💡 **快速开始**：发送 /help 查看详细帮助"

    HELP_MSG = [
        ".",
        "**🎯 功能概述**\n\n我是一个功能强大的 Google Drive 文件管理器，支持从多个来源上传文件到你的云盘。\n\n📚 浏览下面的分类了解更多功能。",
        "**🔐 第一步：授权**\n\n在使用任何功能前，你需要授权访问 Google Drive。\n\n📍 命令：`/auth`\n📝 步骤：\n  1. 点击链接授权\n  2. 复制 `code`\n  3. 发送给我\n\n🔑 **撤销**：`/revoke`",
        "**📥 下载文件**\n\n📍 **基础用法**：`/download 链接`\n📍 **自定义名称**：`/download 链接 | 新文件名.mp4`\n⚠️ **文件限制**：最大 10GB",
        "**📹 YouTube 下载**\n\n📍 命令：`/ytdl YouTube链接`\n🎬 示例：`/ytdl https://www.youtube.com/watch?v=...`",
        "**📱 Telegram 媒体**\n\n📌 回复媒体消息，发送 `/download` 即可自动上传。",
        "**📋 自动监听**\n\n📍 **添加**：`/addmonitor 频道ID 关键字`\n📋 **查看**：`/listmonitor`\n🗑️ **删除**：`/delmonitorID`"
    ]

    # 授权相关
    NOT_AUTH = "🔑 **您尚未认证**\n\n在使用任何功能前，你需要授权我访问你的 Google Drive。\n\n➡️ **立即授权**：发送 /auth"
    AUTH_TEXT = "⛓️ **授权链接**\n\n1️⃣ 点击链接登录 Google\n2️⃣ 允许权限\n3️⃣ 复制 `code`\n4️⃣ 发送给我\n\n[🔐 点击授权]({url})"
    AUTH_SUCCESSFULLY = "✅ **授权成功！**\n\n🎉 你的账户已绑定，现在可以开始上传文件了！"
    ALREADY_AUTH = "🔒 **已授权**\n\n你已经绑定了账户。\n🔄 切换账户：`/revoke` 后重新 `/auth`"
    INVALID_AUTH_CODE = "❌ **代码无效**\n\n可能已过期或格式错误，请重新执行 /auth"
    REVOKED = "🔓 **授权已撤销**\n\n账户已解绑。重新使用请发送 /auth"

    # 下载相关
    DOWNLOAD_PREPARING = "⏳ **准备下载中...**\n正在验证链接和文件信息..."
    DOWNLOAD_USAGE = "❌ **参数错误**\n\n📝 **用法**：\n  `/download 链接`\n  `/download 链接 | 文件名`\n\n📌 或回复媒体发送 `/download`"
    DOWNLOADING = "📥 **开始下载**\n链接：`{link}`"
    DOWNLOADED_SUCCESSFULLY = "✅ **下载完成**\n\n📄 文件名：`{filename}`\n💾 大小：`{size}`\n\n⏳ 正在上传到 Drive..."
    DOWNLOAD_FAILED = "❌ **下载失败**\n\n💡 原因：{reason}\n🔄 请稍后重试"

    # 上传相关
    UPLOADED_SUCCESSFULLY = "✅ **上传成功**\n\n[📥 {filename}]({link}) __{size}__\n\n🎉 文件已保存到 Drive"
    UPLOAD_FAILED = "❌ **上传失败**\n\n💡 原因：{reason}\n🔄 请检查后重试"

    # 错误与通用
    PERMISSION_DENIED = "⛔ **权限不足**\n\n仅管理员可以执行此操作。\n📞 请联系 Bot 管理员"
    GROUP_USE_PRIVATE = "⚠️ **请在私聊中使用**\n\n此命令仅限私聊。"
    FILE_NOT_FOUND = "❌ **文件不存在**\n\n请检查文件 ID 或链接是否有效。"
    FILE_TOO_LARGE = "⚠️ **文件过大**\n\n当前限制：**10 GB**"
    WENT_WRONG = "⁉️ **发生错误**\n\n请稍后重试或联系管理员。"
    
    # 保持原有字段以防兼容问题
    RATE_LIMIT_EXCEEDED_MESSAGE = "❗ **超过限速**\n24小时内请求过多，请稍后再试。"
    INVALID_GDRIVE_URL = "❗ **链接无效**\n请提供正确的 Google Drive 链接。"
    COPIED_SUCCESSFULLY = "✅ **复制成功**\n[{}]({})"
    DB_ERROR = "⚠️ **数据库错误**\n请检查配置。"
    INVALID_FILENAME = "❗ **文件名无效**"
    DOWNLOAD_MISSING_URL = "缺少下载链接"
    DOWNLOAD_TYPE_NOT_ALLOWED = "文件类型不支持"
    DOWNLOAD_ONLY_HTTP = "仅支持 HTTP/HTTPS"
    DOWNLOAD_INVALID_URL = "链接无效"
    DOWNLOAD_RESOLVE_FAILED = "无法解析主机"
    DOWNLOAD_FORBIDDEN_DEST = "链接指向受限地址"
    DOWNLOAD_REDIRECT_NO_TARGET = "重定向无目标"
    DOWNLOAD_REDIRECT_INVALID = "重定向无效"
    DOWNLOAD_REDIRECT_LOOP = "重定向循环"
    DOWNLOAD_REDIRECT_TOO_MANY = "重定向过多"
    DOWNLOAD_REPLY_REQUIRED = "请回复媒体消息"
    DOWNLOAD_MEDIA_NOT_FOUND = "未找到媒体"
    DOWNLOAD_FILE_ID_MISSING = "缺少文件 ID"
    DOWNLOAD_FILE_REFERENCE_INVALID = "文件引用无效"
    DOWNLOAD_TOO_MANY_REQUESTS = "请求过快，请 {} 秒后重试"
    DOWNLOAD_INTERNAL_ERROR = "内部错误"
    DOWNLOAD_GENERIC_ERROR = "下载失败"
    DRIVE_CIRCUIT_OPEN = "❗ **服务冷却中**\n错误过多，暂时暂停服务。"
    INVALID_CREDENTIALS = "❗ **凭据失效**\n请重新授权 /auth"
    AUTHMODE_USAGE = "❗ **用法**: /authmode <service|oauth>"
    AUTHMODE_SERVICE_ENABLED = "🔐 **已切换至服务账号**"
    AUTHMODE_OAUTH_ENABLED = "🔑 **已切换至用户模式**"
    AUTHMODE_SERVICE_UNAVAILABLE = "❗ **未配置服务账号**"
    DOWNLOAD_TG_FILE = "📥 **下载 Telegram 文件**\n📄 `{}`\n💾 `{}`"
    PARENT_SET_SUCCESS = "✅ **文件夹设置成功**\nID: `{}`"
    PARENT_CLEAR_SUCCESS = "✅ **文件夹已清除**"
    CURRENT_PARENT = "🆔 **当前文件夹 ID**: `{}`"
    NOT_FOLDER_LINK = "❗ **链接无效**\n这不是一个文件夹链接。"
    CLONING = "🗂️ **正在克隆...**"
    PROVIDE_GDRIVE_URL = "❗ **请提供链接**"
    MIRROR_NO_PERMISSION = "⚠️ 无权限"
    MIRROR_PROVIDE_URL = "⚠️ 请提供 URL"
    MIRROR_UNSUPPORTED_PROTOCOL = "⚠️ 仅支持 HTTP(S)"
    INSUFFICIENT_PERMISSONS = "❗ **权限不足**"
    DELETED_SUCCESSFULLY = "🗑️ **删除成功**"
    EMPTY_TRASH = "🗑️ **垃圾箱已清空**"
    PROVIDE_YTDL_LINK = "❗ **请提供 YouTube 链接**"
    LIST_HEADER = "📂 **目录: {}**"
    LIST_EMPTY = "📂 **目录为空**"
    LIST_ERROR = "❗ **获取失败**: {}"
    MIRROR_SUBMIT_FAILED = "❗ **任务提交失败**"
    SEARCH_USAGE = "🔍 **用法**: /searchdrive 关键字"
    SEARCH_NO_RESULTS = "🔍 **无结果**: {}"
    SEARCH_RESULTS_HEADER = "🔍 **搜索结果**: {}"
    SEARCH_PAGE_TOKEN = "▶️ **下一页**: `{}`"
