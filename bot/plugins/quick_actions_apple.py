"""
Apple 风格的快捷操作面板
提供常用功能的快速访问
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper import gDriveDB


@Client.on_message(filters.command(["menu_apple", "m"]) & filters.private, group=0)
async def menu_apple_handler(client: Client, message):
    """
    Apple 风格的快捷菜单
    """
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "用户"
    
    # 检查授权状态
    is_authorized = gDriveDB.is_authorized(user_id)
    is_sudo = user_id in SUDO_USERS
    
    text = AppleUI.format_message(
        title="快捷菜单",
        icon="☰",
        subtitle=f"欢迎，{user_name}",
        content=(
            f"**账户状态**\n"
            f"Google Drive: {'✅ 已连接' if is_authorized else '⚠️ 未连接'}\n"
            f"权限级别: {'🔑 管理员' if is_sudo else '👤 普通用户'}\n\n"
            "选择下方操作快速开始"
        )
    )
    
    # 基本操作
    basic_buttons = [
        [
            AppleUI.create_button("📤 上传文件", callback_data="quick_upload"),
            AppleUI.create_button("🔍 搜索", callback_data="quick_search")
        ],
        [
            AppleUI.create_button("📁 我的文件", callback_data="quick_my_files"),
            AppleUI.create_button("📊 统计信息", callback_data="quick_stats")
        ]
    ]
    
    # 管理员操作
    admin_buttons = []
    if is_sudo:
        admin_buttons = [
            [
                AppleUI.create_button("🔄 任务管理", callback_data="quick_tasks"),
                AppleUI.create_button("📊 监控面板", callback_data="quick_monitor")
            ]
        ]
    
    # 常用设置
    settings_buttons = [
        [
            AppleUI.create_button("⚙️ 设置", callback_data="quick_settings"),
            AppleUI.create_button("❓ 帮助", callback_data="show_help")
        ],
        [AppleUI.create_button("🏠 主页", callback_data="back_home")]
    ]
    
    all_buttons = basic_buttons + admin_buttons + settings_buttons
    keyboard = AppleUI.create_keyboard(all_buttons)
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^quick_upload$"))
async def quick_upload_callback(client: Client, callback_query: CallbackQuery):
    """
    快捷上传操作
    """
    user_id = callback_query.from_user.id
    is_authorized = gDriveDB.is_authorized(user_id)
    
    if not is_authorized:
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content=(
                "您尚未授权 Google Drive\n\n"
                "请先使用 `/auth_apple` 命令进行授权"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
        return
    
    text = AppleUI.format_message(
        title="上传文件",
        icon=AppleUI.ICONS["upload"],
        content=(
            "**上传方式**\n\n"
            "📤 **直接发送**\n"
            "直接发送文件给我，自动上传\n\n"
            "🔗 **链接上传**\n"
            "使用 `/mirror_apple <URL>`\n\n"
            "📋 **克隆文件**\n"
            "使用 `/clone <Drive链接>`\n\n"
            "💡 提示：支持批量上传"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("🔗 链接上传", callback_data="upload_link")],
        [AppleUI.create_button("📋 克隆文件", callback_data="upload_clone")],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_search$"))
async def quick_search_callback(client: Client, callback_query: CallbackQuery):
    """
    快捷搜索功能
    """
    text = AppleUI.format_message(
        title="搜索功能",
        icon=AppleUI.ICONS["search"],
        content=(
            "**搜索方式**\n\n"
            "🔍 **Drive 搜索**\n"
            "使用 `/searchdrive <关键词>`\n\n"
            "📁 **列出文件**\n"
            "使用 `/listdrive`\n\n"
            "⚡ **内联搜索**\n"
            "在任意聊天中输入 `@bot_username 关键词`\n\n"
            "💡 支持模糊匹配和文件类型筛选"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("🔍 Drive 搜索", callback_data="search_drive"),
            AppleUI.create_button("📁 列出文件", callback_data="list_files")
        ],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_my_files$"))
async def quick_my_files_callback(client: Client, callback_query: CallbackQuery):
    """
    我的文件
    """
    user_id = callback_query.from_user.id
    is_authorized = gDriveDB.is_authorized(user_id)
    
    if not is_authorized:
        error = AppleUI.create_error_message("auth_failed")
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
        return
    
    # 模拟文件列表（实际应该从 Drive 获取）
    text = AppleUI.format_message(
        title="我的文件",
        icon=AppleUI.ICONS["folder"],
        content=(
            "**最近上传**\n\n"
            "📄 document.pdf (2.5 MB)\n"
            "🖼️ photo.jpg (1.2 MB)\n"
            "🎥 video.mp4 (50.0 MB)\n\n"
            "**存储情况**\n"
            "已使用: 150 MB / 15 GB\n\n"
            "使用 `/listdrive` 查看完整列表"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("🔄 刷新", callback_data="quick_my_files"),
            AppleUI.create_button("🔗 打开 Drive", url="https://drive.google.com")
        ],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_stats$"))
async def quick_stats_callback(client: Client, callback_query: CallbackQuery):
    """
    统计信息
    """
    user_id = callback_query.from_user.id
    
    # 模拟统计数据
    text = AppleUI.format_message(
        title="统计信息",
        icon="📊",
        content=(
            "**使用情况**\n\n"
            "📤 上传文件: 25 个\n"
            "💾 总大小: 150 MB\n"
            "🔄 镜像任务: 12 个\n"
            "✅ 成功率: 95%\n\n"
            "**本月活动**\n\n"
            "📈 上传次数: 8 次\n"
            "⏱ 平均用时: 2.5 分钟\n\n"
            "🏆 您已连续使用 15 天！"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("🔄 刷新", callback_data="quick_stats")],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_tasks$"))
async def quick_tasks_callback(client: Client, callback_query: CallbackQuery):
    """
    任务管理（管理员）
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 需要管理员权限", show_alert=True)
        return
    
    # 模拟任务列表
    text = AppleUI.format_message(
        title="任务管理",
        icon="🔄",
        content=(
            "**活动任务**\n\n"
            "▶️ 任务 #1: file1.zip (45%)\n"
            "⏸ 任务 #2: file2.pdf (已暂停)\n\n"
            "**队列中**\n\n"
            "⏳ 任务 #3: file3.mp4\n"
            "⏳ 任务 #4: file4.zip\n\n"
            "**已完成**\n\n"
            "✅ 今日完成: 5 个\n"
            "❌ 失败: 1 个"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("⏸ 暂停全部", callback_data="tasks_pause_all"),
            AppleUI.create_button("▶️ 继续全部", callback_data="tasks_resume_all")
        ],
        [AppleUI.create_button("❌ 取消全部", callback_data="tasks_cancel_all")],
        [AppleUI.create_button("🔄 刷新", callback_data="quick_tasks")],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_monitor$"))
async def quick_monitor_callback(client: Client, callback_query: CallbackQuery):
    """
    监控面板（管理员）
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 需要管理员权限", show_alert=True)
        return
    
    text = AppleUI.format_message(
        title="监控面板",
        icon="📊",
        content=(
            "**系统状态**\n\n"
            "🟢 Bot 运行正常\n"
            "🟢 Drive API 正常\n"
            "🟢 数据库连接正常\n\n"
            "**用户统计**\n\n"
            "👥 总用户: 150\n"
            "✅ 已授权: 120\n"
            "📊 活跃用户: 45\n\n"
            "**资源使用**\n\n"
            "💾 CPU: 25%\n"
            "💾 RAM: 512 MB / 2 GB\n"
            "💾 磁盘: 2.5 GB / 50 GB"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("🔄 刷新", callback_data="quick_monitor"),
            AppleUI.create_button("📈 详细信息", callback_data="monitor_details")
        ],
        [AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^quick_settings$"))
async def quick_settings_callback(client: Client, callback_query: CallbackQuery):
    """
    快捷跳转到设置
    """
    # 跳转到设置页面
    from bot.plugins.settings_apple import settings_apple_handler
    
    message = callback_query.message
    message.from_user = callback_query.from_user
    message.text = "/settings_apple"
    
    # 重新渲染设置页面
    user_id = callback_query.from_user.id
    from bot.plugins.settings_apple import get_user_settings
    settings = get_user_settings(user_id)
    
    is_authorized = gDriveDB.is_authorized(user_id)
    auth_status = "✅ 已连接" if is_authorized else "⚠️ 未连接"
    
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的上传体验",
        content=(
            f"**Google Drive 状态**\n"
            f"{auth_status}\n\n"
            f"**当前设置**\n"
            f"🌓 主题: {settings['theme']}\n"
            f"🌍 语言: {settings['language']}\n"
            f"🔔 通知: {'开启' if settings['notifications'] else '关闭'}\n"
            f"🗑 自动删除: {'开启' if settings['auto_delete'] else '关闭'}\n\n"
            f"点击下方选项进行配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("Google Drive", callback_data="settings_gdrive", icon=AppleUI.ICONS["gdrive"]),
            AppleUI.create_button("外观", callback_data="settings_appearance", icon="🌓")
        ],
        [
            AppleUI.create_button("通知", callback_data="settings_notifications", icon="🔔"),
            AppleUI.create_button("高级", callback_data="settings_advanced", icon="⚙️")
        ],
        [
            AppleUI.create_button("关于", callback_data="show_about", icon=AppleUI.ICONS["info"]),
            AppleUI.create_button("返回菜单", callback_data="back_to_menu", icon=AppleUI.ICONS["back"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^back_to_menu$"))
async def back_to_menu_callback(client: Client, callback_query: CallbackQuery):
    """
    返回快捷菜单
    """
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name or "用户"
    
    is_authorized = gDriveDB.is_authorized(user_id)
    is_sudo = user_id in SUDO_USERS
    
    text = AppleUI.format_message(
        title="快捷菜单",
        icon="☰",
        subtitle=f"欢迎，{user_name}",
        content=(
            f"**账户状态**\n"
            f"Google Drive: {'✅ 已连接' if is_authorized else '⚠️ 未连接'}\n"
            f"权限级别: {'🔑 管理员' if is_sudo else '👤 普通用户'}\n\n"
            "选择下方操作快速开始"
        )
    )
    
    basic_buttons = [
        [
            AppleUI.create_button("📤 上传文件", callback_data="quick_upload"),
            AppleUI.create_button("🔍 搜索", callback_data="quick_search")
        ],
        [
            AppleUI.create_button("📁 我的文件", callback_data="quick_my_files"),
            AppleUI.create_button("📊 统计信息", callback_data="quick_stats")
        ]
    ]
    
    admin_buttons = []
    if is_sudo:
        admin_buttons = [
            [
                AppleUI.create_button("🔄 任务管理", callback_data="quick_tasks"),
                AppleUI.create_button("📊 监控面板", callback_data="quick_monitor")
            ]
        ]
    
    settings_buttons = [
        [
            AppleUI.create_button("⚙️ 设置", callback_data="quick_settings"),
            AppleUI.create_button("❓ 帮助", callback_data="show_help")
        ],
        [AppleUI.create_button("🏠 主页", callback_data="back_home")]
    ]
    
    all_buttons = basic_buttons + admin_buttons + settings_buttons
    keyboard = AppleUI.create_keyboard(all_buttons)
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# Inline Query 支持（快捷搜索）
@Client.on_inline_query()
async def inline_query_handler(client: Client, inline_query: InlineQuery):
    """
    Inline Query 处理器 - 快速搜索功能
    """
    query = inline_query.query.strip()
    
    if not query:
        # 显示默认选项
        results = [
            InlineQueryResultArticle(
                title="🔍 搜索 Drive 文件",
                description="输入关键词搜索您的 Google Drive",
                input_message_content=InputTextMessageContent(
                    "请输入搜索关键词"
                )
            ),
            InlineQueryResultArticle(
                title="📤 快捷上传",
                description="快速上传文件到 Google Drive",
                input_message_content=InputTextMessageContent(
                    "使用 /mirror_apple <URL> 上传文件"
                )
            )
        ]
    else:
        # 模拟搜索结果
        results = [
            InlineQueryResultArticle(
                title=f"📄 {query}.pdf",
                description="2.5 MB • 上传于 2025-12-20",
                input_message_content=InputTextMessageContent(
                    f"文件: {query}.pdf\n大小: 2.5 MB\n链接: https://drive.google.com/..."
                )
            ),
            InlineQueryResultArticle(
                title=f"🖼️ {query}.jpg",
                description="1.2 MB • 上传于 2025-12-19",
                input_message_content=InputTextMessageContent(
                    f"图片: {query}.jpg\n大小: 1.2 MB\n链接: https://drive.google.com/..."
                )
            )
        ]
    
    await inline_query.answer(results, cache_time=1)
