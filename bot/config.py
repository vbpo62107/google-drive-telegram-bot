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
    OneOneFiveAuth = ['115auth', '115login']
    OneOneFiveUpload = ['115upload']


class Messages:
    """改进版的消息常量类 - 统一了 Emoji、文案、格式"""
    
    # ━━━━━━━━━━━━━━━━━━━ 欢迎和帮助消息 ━━━━━━━━━━━━━━━━━━━
    START_MSG = (
        "👋 **欢迎使用 Google Drive 上传器**\n\n"
        "🤖 我是一个专业的文件上传助手，可以帮你：\n"
        "  • 📥 从直链下载文件到服务器\n"
        "  • 📤 自动上传到你的 Google Drive\n"
        "  • 🎬 支持 YouTube 视频下载\n"
        "  • 📡 自动监听频道并捕获文件\n"
        "  • 🔍 搜索和管理 Drive 文件\n\n"
        "💡 **快速开始**：发送 /help 查看详细帮助"
    )

    HELP_MSG = [
        ".",
        (
            "**🎯 功能概述**\n\n"
            "我是一个功能强大的 Google Drive 文件管理器，"
            "支持从多个来源上传文件到你的云盘。\n\n"
            "📚 浏览下面的分类了解更多功能。"
        ),
        (
            "**🔐 第一步：授权 Google Drive**\n\n"
            "在使用任何功能前，你需要授权我访问你的 Google Drive。\n\n"
            "📍 命令：`/auth`\n"
            "📝 步骤：\n"
            "  1. 点击授权链接\n"
            "  2. 允许权限请求\n"
            "  3. 复制返回页面中的 `code`\n"
            "  4. 发送 `code` 给我\n\n"
            "🔑 **撤销授权**：`/revoke` 将取消当前账户的访问权限"
        ),
        (
            "**📥 下载直链文件**\n\n"
            "我可以从互联网直链下载文件，然后上传到你的 Drive。\n\n"
            "📍 **基础用法**：`/download 链接`\n"
            "📍 **自定义名称**：`/download 链接 | 新文件名.mp4`\n\n"
            "✨ **支持的格式**：视频、音频、文档、压缩包等\n"
            "⚠️ **文件限制**：最大 10GB"
        ),
        (
            "**📹 YouTube 视频下载**\n\n"
            "使用 yt-dlp 下载 YouTube 和其他视频网站的内容。\n\n"
            "📍 命令：`/ytdl YouTube链接`\n"
            "🎬 示例：`/ytdl https://www.youtube.com/watch?v=...`\n\n"
            "💡 **提示**：同时支持 Bilibili、抖音等平台"
        ),
        (
            "**📱 上传 Telegram 媒体**\n\n"
            "直接转发或回复 Telegram 中的媒体文件到我，"
            "我会自动上传到你的 Google Drive。\n\n"
            "📌 **步骤**：回复媒体消息，发送 `/download` 即可\n"
            "💬 **自定义名称**：`/download | 新文件名`"
        ),
        (
            "**🗂️ 管理自定义文件夹**\n\n"
            "设置一个默认的上传文件夹，所有文件都会上传到这里。\n\n"
            "📍 **设置文件夹**：`/setfolder Google_Drive_文件夹链接`\n"
            "🆔 **查看当前**：`/setfolder`\n"
            "🗑️ **清除设置**：`/setfolder clear`"
        ),
        (
            "**🔍 搜索文件**\n\n"
            "快速搜索你 Google Drive 中的文件。\n\n"
            "📍 命令：`/searchdrive 关键字`\n"
            "📝 支持分页：`/searchdrive 关键字 | 分页标记`\n\n"
            "💡 **提示**：搜索结果包含文件 ID，可用于其他操作"
        ),
        (
            "**📂 浏览文件夹**\n\n"
            "浏览你 Drive 中的文件夹内容。\n\n"
            "📍 **查看根目录**：`/listdrive`\n"
            "📍 **浏览子文件夹**：`/listdrive 文件夹ID`\n\n"
            "✨ **功能**：显示文件列表、大小和共享状态"
        ),
        (
            "**📋 自动监听频道**\n\n"
            "设置关键字监听，当频道中出现匹配内容时自动下载并上传。\n\n"
            "📍 **添加监听**：`/addmonitor 频道ID 关键字1,关键字2`\n"
            "📋 **查看所有**：`/listmonitor`\n"
            "🔄 **切换状态**：`/togglemonitor 监听ID`\n"
            "🗑️ **删除监听**：`/delmonitor 监听ID`"
        ),
        (
            "**🔐 授权模式切换**\n\n"
            "切换 OAuth 用户模式和服务账号模式。\n\n"
            "📍 **查看当前**：`/authmode`\n"
            "📍 **用户模式**：`/authmode oauth`\n"
            "📍 **服务账号**：`/authmode service`"
        ),
        (
            "**⚙️ 其他常用命令**\n\n"
            "📋 **查看状态**：`/status`\n"
            "📁 **列出文件**：`/listdrive`\n"
            "🗑️ **删除文件**：`/delete 文件URL`\n"
            "📋 **复制文件**：`/copy 源文件URL`\n"
            "🗑️🗑️ **清空垃圾**：`/emptytrash`"
        ),
        "**⚠️ 使用规则**\n\n"
        "  1. ⏱️ 一次只发一个请求\n"
        "  2. 🔗 使用高速直链，避免缓慢链接\n"
        "  3. 📦 大文件分割上传\n"
        "  4. ⛔ 禁止滥用（禁用大量并发）",
    ]

    # ━━━━━━━━━━━━━━━━━━━ 授权相关 ━━━━━━━━━━━━━━━━━━━
    NOT_AUTH = (
        "🔑 **您尚未认证**\n\n"
        "在使用任何功能前，你需要授权我访问你的 Google Drive。\n\n"
        "➡️ **立即授权**：发送 /auth"
    )
    
    AUTH_TEXT = (
        "⛓️ **Google Drive 授权链接**\n\n"
        "1️⃣ 点击下面的链接打开授权页面\n"
        "2️⃣ 登录你的 Google 账号\n"
        "3️⃣ 允许所有权限请求\n"
        "4️⃣ 复制浏览器地址栏中的 `code` 参数\n"
        "5️⃣ 粘贴 `code` 给我\n\n"
        "[🔐 点击此处进行授权]({url})\n\n"
        "💡 **或者复制完整链接**：\n```\n{url}\n```"
    )
    
    AUTH_SUCCESSFULLY = (
        "✅ **授权成功！**\n\n"
        "🎉 你的 Google Drive 账户已成功绑定\n"
        "现在你可以开始使用所有功能了！\n\n"
        "📌 下一步：发送一个下载链接或媒体文件"
    )
    
    ALREADY_AUTH = (
        "🔒 **已授权**\n\n"
        "你已经绑定了一个 Google Drive 账户。\n\n"
        "🔄 要切换账户：`/revoke` 然后重新 `/auth`\n"
        "💬 现在你可以开始上传文件了！"
    )
    
    INVALID_AUTH_CODE = (
        "❌ **授权代码无效**\n\n"
        "原因可能是：\n"
        "  • 代码已过期（有效期 10 分钟）\n"
        "  • 代码已被使用过\n"
        "  • 代码格式不正确\n\n"
        "💡 **解决方案**：重新执行 /auth 获取新代码"
    )
    
    REVOKED = (
        "🔓 **授权已撤销**\n\n"
        "你的 Google Drive 账户已从本 Bot 中移除。\n\n"
        "🔄 要重新使用，请发送 /auth"
    )

    # ━━━━━━━━━━━━━━━━━━━ 下载相关 ━━━━━━━━━━━━━━━━━━━
    DOWNLOAD_PREPARING = (
        "⏳ **准备下载中...**\n"
        "正在验证链接和文件信息..."
    )

    DOWNLOAD_USAGE = (
        "❌ **参数错误**\n\n"
        "📝 **正确用法**：\n"
        "  `/download 链接` - 下载文件\n"
        "  `/download 链接 | 新名称.mp4` - 自定义文件名\n\n"
        "📌 **回复媒体**：回复 Telegram 媒体，发送 `/download` 即可\n\n"
        "💡 **示例**：\n"
        "`/download https://example.com/video.mp4`\n"
        "`/download https://example.com/video.mp4 | 我的视频.mp4`"
    )

    DOWNLOADING = (
        "📥 **开始下载**\n"
        "链接：`{link}`"
    )

    DOWNLOADED_SUCCESSFULLY = (
        "✅ **下载完成**\n\n"
        "📄 文件名：`{filename}`\n"
        "💾 文件大小：`{size}`\n\n"
        "⏳ 正在上传到 Google Drive..."
    )

    DOWNLOAD_FAILED = (
        "❌ **下载失败**\n\n"
        "💡 原因：{reason}\n\n"
        "🔄 请稍后重试"
    )

    # ━━━━━━━━━━━━━━━━━━━ 上传相关 ━━━━━━━━━━━━━━━━━━━
    UPLOADED_SUCCESSFULLY = (
        "✅ **上传成功**\n\n"
        "[📥 {filename}]({link}) __{size}__\n\n"
        "🎉 文件已保存到你的 Google Drive"
    )

    UPLOAD_FAILED = (
        "❌ **上传失败**\n\n"
        "💡 原因：{reason}\n\n"
        "🔄 请检查后重试"
    )

    # ━━━━━━━━━━━━━━━━━━━ 权限相关 ━━━━━━━━━━━━━━━━━━━
    PERMISSION_DENIED = (
        "⛔ **权限不足**\n\n"
        "你没有权限使用此命令。\n"
        "仅管理员可以执行此操作。\n\n"
        "📞 请联系 Bot 管理员"
    )

    GROUP_USE_PRIVATE = (
        "⚠️ **请在私聊中使用**\n\n"
        "此命令只能在与 Bot 的私聊中使用。\n\n"
        "💬 请点击 @bot_username 开始私聊"
    )

    # ━━━━━━━━━━━━━━━━━━━ 文件相关 ━━━━━━━━━━━━━━━━━━━
    FILE_NOT_FOUND = (
        "❌ **文件不存在**\n\n"
        "🆔 文件 ID：`{file_id}`\n"
        "确保文件存在且你有访问权限"
    )

    INVALID_GDRIVE_URL = (
        "❌ **Google Drive 链接无效**\n\n"
        "请确保：\n"
        "  • 链接格式正确\n"
        "  • 使用的是分享链接\n"
        "  • 链接仍然有效\n\n"
        "💡 从 Google Drive 右键点击文件 > 获取链接"
    )

    FILE_TOO_LARGE = (
        "⚠️ **文件过大**\n\n"
        "当前限制：**10 GB**\n\n"
        "💡 解决方案：\n"
        "  • 分割文件为多个较小的部分\n"
        "  • 压缩文件后重试\n"
        "  • 联系管理员提高限制"
    )

    # ━━━━━━━━━━━━━━━━━━━ 错误与异常 ━━━━━━━━━━━━━━━━━━━
    DB_ERROR = (
        "⚠️ **数据库错误**\n\n"
        "数据库访问失败。\n\n"
        "🔍 请检查：\n"
        "  • DATABASE_URL 配置\n"
        "  • 数据库服务是否正常\n"
        "  • 网络连接"
    )

    WENT_WRONG = (
        "⁉️ **出现错误**\n\n"
        "发生了一个意外错误。\n\n"
        "🔧 请稍后重试，或：\n"
        "  • 查看日志了解详情\n"
        "  • 在支持群中反馈问题\n"
        "  • 重启 Bot"
    )

    # ━━━━━━━━━━━━━━━━━━━ 文件列表相关 ━━━━━━━━━━━━━━━━━━━
    LIST_DEFAULT_LABEL = "默认目录"
    LIST_HEADER = "📂 **目录: {}**"
    LIST_EMPTY = "📂 **目录为空**"
    LIST_CONT_HEADER = "📂 **目录内容 (续)**\n**路径:** `{}`\n**ID:** `{}`"
    LIST_PATH_NOT_FOUND = "❗ **未找到路径段:** `{}`"
    LIST_ERROR = "❗ **获取目录内容失败**\n{}"

    # ━━━━━━━━━━━━━━━━━━━ 搜索相关 ━━━━━━━━━━━━━━━━━━━
    SEARCH_USAGE = "❗ **请提供搜索关键字**\n用法 - /{} 关键字 或 /{} 关键字 | 下一页标记"
    SEARCH_ERROR = "❗ **搜索失败**\n{}"
    SEARCH_NO_RESULTS = "🔍 **没有找到匹配的文件或文件夹**\n关键字: `{}`"
    SEARCH_RESULTS_HEADER = "🔍 **搜索结果**\n关键字: `{}`"
    SEARCH_PAGE_TOKEN = "▶️ **下一页标记:** `{}`"

    # ━━━━━━━━━━━━━━━━━━━ 镜像和任务相关 ━━━━━━━━━━━━━━━━━━━
    MIRROR_NO_PERMISSION = "⚠️ **权限不足**"
    MIRROR_PROVIDE_URL = "⚠️ **请提供 URL**"
    MIRROR_UNSUPPORTED_PROTOCOL = "⚠️ **仅支持 HTTP(S) 协议**"
    MIRROR_SUBMIT_FAILED = "❗ **创建镜像任务失败**\n{}\n错误摘要：{}"
    MIRROR_SUBMIT_PERMISSION_TIP = "请检查机器人对下载目录、数据库或 Drive 授权的访问权限后再试。"
    MIRROR_SUBMIT_NETWORK_TIP = "请确认网络连接正常，稍后重新尝试创建任务。"
    MIRROR_SUBMIT_RETRY_TIP = "请稍后重试，若持续失败可在支持群反馈。"

    # ━━━━━━━━━━━━━━━━━━━ 文件夹相关 ━━━━━━━━━━━━━━━━━━━
    PARENT_SET_SUCCESS = "🆔✅ **自定义文件夹链接设置成功**\n自定义文件夹ID - {}\n使用 `/setfolder clear` 来清除设置"
    PARENT_CLEAR_SUCCESS = "🆔🚮 **自定义文件夹ID已成功清除**\n使用 `/setfolder 文件夹链接` 来重新设置"
    CURRENT_PARENT = "🆔 **您当前的自定义文件夹ID - {}**\n使用 `/setfolder 文件夹链接` 来更改设置"

    # ━━━━━━━━━━━━━━━━━━━ 其他杂项 ━━━━━━━━━━━━━━━━━━━
    INSUFFICIENT_PERMISSONS = "❗ **您对此文件的权限不足**\n文件ID - {}"
    DELETED_SUCCESSFULLY = "🗑️✅ **文件删除成功**\n文件ID - {}"
    EMPTY_TRASH = "🗑️🚮 **成功清空垃圾箱！**"
    PROVIDE_YTDL_LINK = "❗ **提供有效的YouTube-DL支持的链接**"
    MONITOR_NOT_FOUND = "❌ **监听项不存在**\n请检查监听 ID 是否正确\n使用 /listmonitor 查看所有监听"
    CLONING = "🗂️ **克隆到Google云端硬盘...**\n Drive 链接 - {}"
    PROVIDE_GDRIVE_URL = "❗ **请提供链接**"
    NOT_FOLDER_LINK = "❗ **链接无效**\n这不是一个文件夹链接。"

    # ━━━━━━━━━━━━━━━━━━━ 下载和上传进度反馈 ━━━━━━━━━━━━━━━━━━━
    DOWNLOAD_TG_FILE = "📥 **下载 Telegram 文件**\n文件名: `{}`\n大小: `{}`"

    # ━━━━━━━━━━━━━━━━━━━ 身份验证相关 ━━━━━━━━━━━━━━━━━━━
    INVALID_CREDENTIALS = "❗ **凭据失效**\n请重新授权 /auth"
    AUTHMODE_USAGE = "❗ **用法**: /authmode <service|oauth>"
    AUTHMODE_SERVICE_ENABLED = "🔐 **已切换至服务账号**"
    AUTHMODE_OAUTH_ENABLED = "🔑 **已切换至用户模式**"
    AUTHMODE_SERVICE_UNAVAILABLE = "❗ **未配置服务账号**"

    # ━━━━━━━━━━━━━━━━━━━ 速率限制和电路断路 ━━━━━━━━━━━━━━━━━━━
    RATE_LIMIT_EXCEEDED_MESSAGE = "❗ **超过限速**\n24小时内请求过多，请稍后再试。"
    DRIVE_CIRCUIT_OPEN = "❗ **服务冷却中**\n错误过多，暂时暂停服务。"

    # ━━━━━━━━━━━━━━━━━━━ 下载错误详情 ━━━━━━━━━━━━━━━━━━━
    DOWNLOAD_MISSING_URL = "❗ **缺少下载链接**"
    DOWNLOAD_TYPE_NOT_ALLOWED = "❗ **文件类型不支持**"
    DOWNLOAD_ONLY_HTTP = "❗ **仅支持 HTTP/HTTPS**"
    DOWNLOAD_INVALID_URL = "❗ **链接无效**"
    DOWNLOAD_RESOLVE_FAILED = "❗ **无法解析主机**"
    DOWNLOAD_FORBIDDEN_DEST = "❗ **链接指向受限地址**"
    DOWNLOAD_REDIRECT_NO_TARGET = "❗ **重定向无目标**"
    DOWNLOAD_REDIRECT_INVALID = "❗ **重定向无效**"
    DOWNLOAD_REDIRECT_LOOP = "❗ **重定向循环**"
    DOWNLOAD_REDIRECT_TOO_MANY = "❗ **重定向过多**"
    DOWNLOAD_REPLY_REQUIRED = "❗ **请回复媒体消息**"
    DOWNLOAD_MEDIA_NOT_FOUND = "❗ **未找到媒体**"
    DOWNLOAD_FILE_ID_MISSING = "❗ **缺少文件 ID**"
    DOWNLOAD_FILE_REFERENCE_INVALID = "❗ **文件引用无效**"
    DOWNLOAD_TOO_MANY_REQUESTS = "❗ **请求过快**\n请 {} 秒后重试"
    DOWNLOAD_INTERNAL_ERROR = "❗ **内部错误**"
    DOWNLOAD_GENERIC_ERROR = "❗ **下载失败**"

    # ━━━━━━━━━━━━━━━━━━━ 115 云盘相关 ━━━━━━━━━━━━━━━━━━━
    ONEONEFIVE_AUTH_USAGE = (
        "❗ **115 授权参数错误**\n\n"
        "请按以下格式发送：\n"
        "• `/115auth cookies <Cookies字符串>` - 使用 Cookies 授权\n"
        "• `/115auth token <token> [app_id]` - 使用 token 授权，可选 app_id\n"
        "• `/115auth info` - 查看当前授权状态"
    )
    ONEONEFIVE_AUTH_SAVED = "✅ **115 授权已保存**\n方式：{method}\n时间：{updated_at}"
    ONEONEFIVE_AUTH_FAILED = "❌ **115 授权保存失败**\n原因：{reason}"
    ONEONEFIVE_AUTH_REQUIRED = (
        "🔑 **未找到 115 授权**\n\n"
        "请先使用 `/115auth cookies <Cookies>` 或 `/115auth token <token> [app_id]` 完成授权。"
    )
    ONEONEFIVE_AUTH_INFO = (
        "🔐 **115 授权状态**\n方式：{method}\n更新时间：{updated_at}\n\n"
        "如需更新，重新发送 /115auth。"
    )
    ONEONEFIVE_UPLOAD_PREPARING = (
        "📤 **准备上传到 115...**\n"
        "文件：{filename}\n"
        "目标目录：{pid}"
    )
    ONEONEFIVE_UPLOAD_SUCCESS = (
        "✅ **115 上传成功**\n"
        "文件：`{filename}`\n"
        "分享链接：{share_url}\n"
        "{extra_lines}"
    )
    ONEONEFIVE_UPLOAD_FAILED = (
        "❌ **115 上传失败**\n"
        "原因：{reason}"
    )
    ONEONEFIVE_RECENT_FILE_MISSING = (
        "❗ **未找到可用的本地文件**\n"
        "请先完成一次下载或镜像任务，或在命令中提供文件路径。\n\n"
        "用法：`/115upload [本地文件路径或名称] | [115 目录ID]`"
    )

    # ━━━━━━━━━━━━━━━━━━━ 其他兼容性字段 ━━━━━━━━━━━━━━━━━━━
    INVALID_FILENAME = "❗ **文件名无效**"
    COPIED_SUCCESSFULLY = "✅ **复制成功**\n[{}]({})"
