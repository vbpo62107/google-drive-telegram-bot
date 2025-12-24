"""
Apple 风格的设置界面
提供完整的个性化配置选项
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper import gDriveDB


# 用户设置存储（简化版，实际应该使用数据库）
user_settings = {}


def get_user_settings(user_id: int) -> dict:
    """获取用户设置"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "language": "zh_CN",
            "theme": "auto",
            "notifications": True,
            "auto_delete": False,
            "default_folder": None,
            "compress_files": False,
        }
    return user_settings[user_id]


def update_user_setting(user_id: int, key: str, value) -> None:
    """更新用户设置"""
    settings = get_user_settings(user_id)
    settings[key] = value
    LOGGER.info(f"Updated setting for user {user_id}: {key} = {value}")


@Client.on_message(filters.command(["settings", "set"]) & filters.private, group=0)
async def settings_handler(client: Client, message):
    """
    Apple 风格的设置主菜单
    """
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    # 获取授权状态
    is_authorized = gDriveDB.is_authorized(user_id)
    auth_status = "✅ 已连接" if is_authorized else "❌ 未连接"
    
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的使用体验",
        content=(
            f"**账户状态**\n"
            f"Google Drive: {auth_status}\n\n"
            "点击下方选项进行配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("☁️  Google Drive", callback_data="settings_gdrive")],
        [
            AppleUI.create_button("🌐  语言", callback_data="settings_language"),
            AppleUI.create_button("🎨  主题", callback_data="settings_theme")
        ],
        [
            AppleUI.create_button("🔔  通知", callback_data="settings_notifications"),
            AppleUI.create_button("📁  默认文件夹", callback_data="settings_folder")
        ],
        [
            AppleUI.create_button("🗜  压缩选项", callback_data="settings_compress"),
            AppleUI.create_button("🗑  自动清理", callback_data="settings_autodel")
        ],
        [AppleUI.create_button("🔄  重置所有设置", callback_data="settings_reset")],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^settings_gdrive$"))
async def settings_gdrive_callback(client: Client, callback_query: CallbackQuery):
    """Google Drive 设置"""
    user_id = callback_query.from_user.id
    is_authorized = gDriveDB.is_authorized(user_id)
    
    if is_authorized:
        text = AppleUI.format_message(
            title="Google Drive",
            icon="☁️",
            content=(
                "**连接状态**: ✅ 已连接\n\n"
                "您可以管理您的 Google Drive 授权"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("查看文件", callback_data="list_files", icon=AppleUI.ICONS["folder"])],
            [AppleUI.create_button("重新授权", callback_data="start_auth", icon=AppleUI.ICONS["refresh"])],
            [AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["delete"])],
            [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
        ])
    else:
        text = AppleUI.format_message(
            title="Google Drive",
            icon="☁️",
            content=(
                "**连接状态**: ❌ 未连接\n\n"
                "连接 Google Drive 以使用所有功能"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即连接", callback_data="start_auth", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
        ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_language$"))
async def settings_language_callback(client: Client, callback_query: CallbackQuery):
    """语言设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    current_lang = settings.get("language", "zh_CN")
    
    lang_options = {
        "zh_CN": "🇨🇳 简体中文",
        "zh_TW": "🇭🇰 繁體中文",
        "en_US": "🇺🇸 English",
        "ja_JP": "🇯🇵 日本語",
    }
    
    text = AppleUI.format_message(
        title="语言设置",
        icon="🌐",
        content=(
            f"**当前语言**: {lang_options.get(current_lang, '未知')}\n\n"
            "选择您偏好的界面语言"
        )
    )
    
    buttons = []
    for lang_code, lang_name in lang_options.items():
        mark = "✓ " if lang_code == current_lang else ""
        buttons.append([AppleUI.create_button(
            f"{mark}{lang_name}",
            callback_data=f"set_lang_{lang_code}"
        )])
    
    buttons.append([AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])])
    
    keyboard = AppleUI.create_keyboard(buttons)
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^set_lang_"))
async def set_language_callback(client: Client, callback_query: CallbackQuery):
    """设置语言"""
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.replace("set_lang_", "")
    
    update_user_setting(user_id, "language", lang_code)
    
    await callback_query.answer("✅ 语言已更新", show_alert=True)
    # 重新显示语言设置页面
    await settings_language_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_theme$"))
async def settings_theme_callback(client: Client, callback_query: CallbackQuery):
    """主题设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    current_theme = settings.get("theme", "auto")
    
    theme_options = {
        "light": "☀️ 浅色模式",
        "dark": "🌙 深色模式",
        "auto": "🔄 跟随系统",
    }
    
    text = AppleUI.format_message(
        title="主题设置",
        icon="🎨",
        content=(
            f"**当前主题**: {theme_options.get(current_theme, '未知')}\n\n"
            "选择您偏好的界面主题\n"
            "（部分功能即将推出）"
        )
    )
    
    buttons = []
    for theme_code, theme_name in theme_options.items():
        mark = "✓ " if theme_code == current_theme else ""
        buttons.append([AppleUI.create_button(
            f"{mark}{theme_name}",
            callback_data=f"set_theme_{theme_code}"
        )])
    
    buttons.append([AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])])
    
    keyboard = AppleUI.create_keyboard(buttons)
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^set_theme_"))
async def set_theme_callback(client: Client, callback_query: CallbackQuery):
    """设置主题"""
    user_id = callback_query.from_user.id
    theme_code = callback_query.data.replace("set_theme_", "")
    
    update_user_setting(user_id, "theme", theme_code)
    
    await callback_query.answer("✅ 主题已更新", show_alert=True)
    await settings_theme_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_notifications$"))
async def settings_notifications_callback(client: Client, callback_query: CallbackQuery):
    """通知设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    enabled = settings.get("notifications", True)
    
    text = AppleUI.format_message(
        title="通知设置",
        icon="🔔",
        content=(
            f"**当前状态**: {'🔔 已启用' if enabled else '🔕 已禁用'}\n\n"
            "控制任务完成、错误等通知的接收"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "🔔 启用通知" if not enabled else "🔕 禁用通知",
            callback_data="toggle_notifications"
        )],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^toggle_notifications$"))
async def toggle_notifications_callback(client: Client, callback_query: CallbackQuery):
    """切换通知状态"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    current = settings.get("notifications", True)
    
    update_user_setting(user_id, "notifications", not current)
    
    status = "禁用" if current else "启用"
    await callback_query.answer(f"✅ 通知已{status}", show_alert=True)
    await settings_notifications_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_folder$"))
async def settings_folder_callback(client: Client, callback_query: CallbackQuery):
    """默认文件夹设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    folder = settings.get("default_folder") or "根目录"
    
    text = AppleUI.format_message(
        title="默认文件夹",
        icon="📁",
        content=(
            f"**当前设置**: `{folder}`\n\n"
            "设置文件上传的默认目标文件夹\n\n"
            "使用 `/setfolder` 命令来更改"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("更改文件夹", callback_data="change_folder", icon=AppleUI.ICONS["folder"])],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_compress$"))
async def settings_compress_callback(client: Client, callback_query: CallbackQuery):
    """压缩选项设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    enabled = settings.get("compress_files", False)
    
    text = AppleUI.format_message(
        title="压缩选项",
        icon="🗜",
        content=(
            f"**当前状态**: {'✅ 已启用' if enabled else '❌ 已禁用'}\n\n"
            "自动压缩大文件后上传\n"
            "可节省存储空间和传输时间"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "✅ 启用压缩" if not enabled else "❌ 禁用压缩",
            callback_data="toggle_compress"
        )],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^toggle_compress$"))
async def toggle_compress_callback(client: Client, callback_query: CallbackQuery):
    """切换压缩选项"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    current = settings.get("compress_files", False)
    
    update_user_setting(user_id, "compress_files", not current)
    
    status = "禁用" if current else "启用"
    await callback_query.answer(f"✅ 压缩已{status}", show_alert=True)
    await settings_compress_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_autodel$"))
async def settings_autodel_callback(client: Client, callback_query: CallbackQuery):
    """自动清理设置"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    enabled = settings.get("auto_delete", False)
    
    text = AppleUI.format_message(
        title="自动清理",
        icon="🗑",
        content=(
            f"**当前状态**: {'✅ 已启用' if enabled else '❌ 已禁用'}\n\n"
            "上传完成后自动删除本地文件\n"
            "节省本地存储空间"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "✅ 启用清理" if not enabled else "❌ 禁用清理",
            callback_data="toggle_autodel"
        )],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^toggle_autodel$"))
async def toggle_autodel_callback(client: Client, callback_query: CallbackQuery):
    """切换自动清理"""
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    current = settings.get("auto_delete", False)
    
    update_user_setting(user_id, "auto_delete", not current)
    
    status = "禁用" if current else "启用"
    await callback_query.answer(f"✅ 自动清理已{status}", show_alert=True)
    await settings_autodel_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_reset$"))
async def settings_reset_callback(client: Client, callback_query: CallbackQuery):
    """重置设置确认"""
    text = AppleUI.format_message(
        title="重置设置",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要重置所有设置吗？\n\n"
            "以下设置将恢复默认值：\n"
            "• 语言和主题\n"
            "• 通知选项\n"
            "• 压缩和清理选项\n\n"
            "⚠️ 此操作不可撤销"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("确认重置", callback_data="confirm_reset", icon=AppleUI.ICONS["delete"])],
        [AppleUI.create_button("取消", callback_data="back_to_settings", icon=AppleUI.ICONS["cancel"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^confirm_reset$"))
async def confirm_reset_callback(client: Client, callback_query: CallbackQuery):
    """确认重置设置"""
    user_id = callback_query.from_user.id
    
    # 删除用户设置
    if user_id in user_settings:
        del user_settings[user_id]
    
    success = AppleUI.create_success_message(
        title="重置完成",
        message="所有设置已恢复为默认值"
    )
    
    text = AppleUI.format_message(
        title=success["title"],
        content=success["message"]
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["settings"])],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 设置已重置")


@Client.on_callback_query(filters.regex(r"^back_to_settings$"))
async def back_to_settings_callback(client: Client, callback_query: CallbackQuery):
    """返回设置主菜单"""
    # 模拟 /settings 命令
    from pyrogram.types import Message
    
    message = callback_query.message
    message.from_user = callback_query.from_user
    message.text = "/settings"
    
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    is_authorized = gDriveDB.is_authorized(user_id)
    auth_status = "✅ 已连接" if is_authorized else "❌ 未连接"
    
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的使用体验",
        content=(
            f"**账户状态**\n"
            f"Google Drive: {auth_status}\n\n"
            "点击下方选项进行配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("☁️  Google Drive", callback_data="settings_gdrive")],
        [
            AppleUI.create_button("🌐  语言", callback_data="settings_language"),
            AppleUI.create_button("🎨  主题", callback_data="settings_theme")
        ],
        [
            AppleUI.create_button("🔔  通知", callback_data="settings_notifications"),
            AppleUI.create_button("📁  默认文件夹", callback_data="settings_folder")
        ],
        [
            AppleUI.create_button("🗜  压缩选项", callback_data="settings_compress"),
            AppleUI.create_button("🗑  自动清理", callback_data="settings_autodel")
        ],
        [AppleUI.create_button("🔄  重置所有设置", callback_data="settings_reset")],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
