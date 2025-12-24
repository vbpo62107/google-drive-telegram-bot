"""
用户个性化设置模块
允许用户自定义界面风格、语言和行为偏好
"""

from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.ui_apple_style import AppleUI


# 用户偏好存储（实际应用中应使用数据库）
user_preferences: Dict[int, dict] = {}


class UserPreferences:
    """用户偏好管理类"""
    
    DEFAULT_PREFERENCES = {
        "language": "zh-CN",
        "theme": "auto",  # auto, light, dark
        "notifications": "all",  # all, important, none
        "animation": True,
        "compact_mode": False,
        "auto_delete": False,
        "default_folder": "root"
    }
    
    LANGUAGE_OPTIONS = {
        "zh-CN": "🇨🇳 简体中文",
        "zh-TW": "🇹🇼 繁體中文",
        "en-US": "🇺🇸 English",
        "ja-JP": "🇯🇵 日本語",
        "ko-KR": "🇰🇷 한국어"
    }
    
    THEME_OPTIONS = {
        "auto": "🌗 自动",
        "light": "☀️ 浅色",
        "dark": "🌙 深色"
    }
    
    @staticmethod
    def get(user_id: int, key: str = None) -> any:
        """获取用户偏好"""
        if user_id not in user_preferences:
            user_preferences[user_id] = UserPreferences.DEFAULT_PREFERENCES.copy()
        
        if key:
            return user_preferences[user_id].get(key, UserPreferences.DEFAULT_PREFERENCES.get(key))
        return user_preferences[user_id]
    
    @staticmethod
    def set(user_id: int, key: str, value: any) -> None:
        """设置用户偏好"""
        if user_id not in user_preferences:
            user_preferences[user_id] = UserPreferences.DEFAULT_PREFERENCES.copy()
        user_preferences[user_id][key] = value
    
    @staticmethod
    def reset(user_id: int) -> None:
        """重置用户偏好"""
        user_preferences[user_id] = UserPreferences.DEFAULT_PREFERENCES.copy()


@Client.on_message(filters.command(["settings", "preferences"]) & filters.private)
async def settings_menu(client: Client, message):
    """
    设置菜单
    使用: /settings 或 /preferences
    """
    user_id = message.from_user.id
    prefs = UserPreferences.get(user_id)
    
    text = AppleUI.format_message(
        title="个性化设置",
        icon=AppleUI.ICONS["settings"],
        content=(
            "**当前设置**\n\n"
            f"🌍 语言: {UserPreferences.LANGUAGE_OPTIONS.get(prefs['language'])}\n"
            f"🎨 主题: {UserPreferences.THEME_OPTIONS.get(prefs['theme'])}\n"
            f"🔔 通知: {prefs['notifications']}\n"
            f"🎬 动画: {'ON' if prefs['animation'] else 'OFF'}\n"
            f"📊 简洁模式: {'ON' if prefs['compact_mode'] else 'OFF'}\n\n"
            "点击下方按钮修改设置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("🌍 语言", callback_data="pref:language"),
            AppleUI.create_button("🎨 主题", callback_data="pref:theme")
        ],
        [
            AppleUI.create_button("🔔 通知", callback_data="pref:notifications"),
            AppleUI.create_button("🎬 动画", callback_data="pref:animation")
        ],
        [
            AppleUI.create_button("📊 简洁模式", callback_data="pref:compact"),
            AppleUI.create_button("🔄 重置", callback_data="pref:reset")
        ],
        [
            AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^pref:"))
async def handle_preference(client: Client, callback_query: CallbackQuery):
    """处理偏好设置回调"""
    user_id = callback_query.from_user.id
    pref_type = callback_query.data.replace("pref:", "")
    
    if pref_type == "language":
        await show_language_options(callback_query)
    elif pref_type == "theme":
        await show_theme_options(callback_query)
    elif pref_type == "notifications":
        await show_notification_options(callback_query)
    elif pref_type == "animation":
        await toggle_animation(callback_query)
    elif pref_type == "compact":
        await toggle_compact_mode(callback_query)
    elif pref_type == "reset":
        await reset_preferences(callback_query)


async def show_language_options(callback_query: CallbackQuery):
    """显示语言选项"""
    text = AppleUI.format_message(
        title="选择语言",
        icon="🌍",
        content="选择您偏好的界面语言"
    )
    
    keyboard_rows = []
    for lang_code, lang_name in UserPreferences.LANGUAGE_OPTIONS.items():
        keyboard_rows.append([
            AppleUI.create_button(
                lang_name,
                callback_data=f"set_lang:{lang_code}"
            )
        ])
    
    keyboard_rows.append([
        AppleUI.create_button(
            "返回设置",
            callback_data="back_to_settings",
            icon=AppleUI.ICONS["back"]
        )
    ])
    
    from pyrogram.types import InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


async def show_theme_options(callback_query: CallbackQuery):
    """显示主题选项"""
    text = AppleUI.format_message(
        title="选择主题",
        icon="🎨",
        content=(
            "选择您喜欢的界面风格\n\n"
            "🌗 自动 - 跟随系统设置\n"
            "☀️ 浅色 - 明亮清新\n"
            "🌙 深色 - 柔和护眼"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("🌗 自动", callback_data="set_theme:auto")],
        [
            AppleUI.create_button("☀️ 浅色", callback_data="set_theme:light"),
            AppleUI.create_button("🌙 深色", callback_data="set_theme:dark")
        ],
        [
            AppleUI.create_button(
                "返回设置",
                callback_data="back_to_settings",
                icon=AppleUI.ICONS["back"]
            )
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


async def show_notification_options(callback_query: CallbackQuery):
    """显示通知选项"""
    text = AppleUI.format_message(
        title="通知设置",
        icon="🔔",
        content=(
            "选择您希望接收的通知类型\n\n"
            "🔔 全部 - 接收所有通知\n"
            "⚠️ 重要 - 只接收重要通知\n"
            "🔕 关闭 - 不接收通知"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("🔔 全部", callback_data="set_notif:all")],
        [AppleUI.create_button("⚠️ 重要", callback_data="set_notif:important")],
        [AppleUI.create_button("🔕 关闭", callback_data="set_notif:none")],
        [
            AppleUI.create_button(
                "返回设置",
                callback_data="back_to_settings",
                icon=AppleUI.ICONS["back"]
            )
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


async def toggle_animation(callback_query: CallbackQuery):
    """切换动画设置"""
    user_id = callback_query.from_user.id
    current = UserPreferences.get(user_id, "animation")
    new_value = not current
    UserPreferences.set(user_id, "animation", new_value)
    
    status = "ON" if new_value else "OFF"
    await callback_query.answer(f"🎬 动画已{status}", show_alert=True)
    
    # 刷新设置页面
    await show_settings_page(callback_query)


async def toggle_compact_mode(callback_query: CallbackQuery):
    """切换简洁模式"""
    user_id = callback_query.from_user.id
    current = UserPreferences.get(user_id, "compact_mode")
    new_value = not current
    UserPreferences.set(user_id, "compact_mode", new_value)
    
    status = "ON" if new_value else "OFF"
    await callback_query.answer(f"📊 简洁模式已{status}", show_alert=True)
    
    await show_settings_page(callback_query)


async def reset_preferences(callback_query: CallbackQuery):
    """重置偏好设置"""
    text = AppleUI.format_message(
        title="重置设置",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要重置所有设置吗？\n\n"
            "这将恢复为默认配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("确认重置", callback_data="confirm_reset", icon=AppleUI.ICONS["delete"]),
            AppleUI.create_button("取消", callback_data="back_to_settings", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^set_lang:"))
async def set_language(client: Client, callback_query: CallbackQuery):
    """设置语言"""
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.replace("set_lang:", "")
    
    UserPreferences.set(user_id, "language", lang_code)
    lang_name = UserPreferences.LANGUAGE_OPTIONS.get(lang_code, lang_code)
    
    await callback_query.answer(f"✅ 语言已设置为 {lang_name}", show_alert=True)
    await show_settings_page(callback_query)


@Client.on_callback_query(filters.regex(r"^set_theme:"))
async def set_theme(client: Client, callback_query: CallbackQuery):
    """设置主题"""
    user_id = callback_query.from_user.id
    theme = callback_query.data.replace("set_theme:", "")
    
    UserPreferences.set(user_id, "theme", theme)
    theme_name = UserPreferences.THEME_OPTIONS.get(theme, theme)
    
    await callback_query.answer(f"✅ 主题已设置为 {theme_name}", show_alert=True)
    await show_settings_page(callback_query)


@Client.on_callback_query(filters.regex(r"^set_notif:"))
async def set_notifications(client: Client, callback_query: CallbackQuery):
    """设置通知"""
    user_id = callback_query.from_user.id
    notif_type = callback_query.data.replace("set_notif:", "")
    
    UserPreferences.set(user_id, "notifications", notif_type)
    
    notif_names = {
        "all": "全部",
        "important": "重要",
        "none": "关闭"
    }
    
    await callback_query.answer(f"✅ 通知已设置为 {notif_names.get(notif_type)}", show_alert=True)
    await show_settings_page(callback_query)


@Client.on_callback_query(filters.regex(r"^confirm_reset$"))
async def confirm_reset(client: Client, callback_query: CallbackQuery):
    """确认重置"""
    user_id = callback_query.from_user.id
    UserPreferences.reset(user_id)
    
    await callback_query.answer("✅ 设置已重置", show_alert=True)
    await show_settings_page(callback_query)


@Client.on_callback_query(filters.regex(r"^back_to_settings$"))
async def back_to_settings(client: Client, callback_query: CallbackQuery):
    """返回设置页面"""
    await show_settings_page(callback_query)


async def show_settings_page(callback_query: CallbackQuery):
    """显示设置页面"""
    user_id = callback_query.from_user.id
    prefs = UserPreferences.get(user_id)
    
    text = AppleUI.format_message(
        title="个性化设置",
        icon=AppleUI.ICONS["settings"],
        content=(
            "**当前设置**\n\n"
            f"🌍 语言: {UserPreferences.LANGUAGE_OPTIONS.get(prefs['language'])}\n"
            f"🎨 主题: {UserPreferences.THEME_OPTIONS.get(prefs['theme'])}\n"
            f"🔔 通知: {prefs['notifications']}\n"
            f"🎬 动画: {'ON' if prefs['animation'] else 'OFF'}\n"
            f"📊 简洁模式: {'ON' if prefs['compact_mode'] else 'OFF'}\n\n"
            "点击下方按钮修改设置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("🌍 语言", callback_data="pref:language"),
            AppleUI.create_button("🎨 主题", callback_data="pref:theme")
        ],
        [
            AppleUI.create_button("🔔 通知", callback_data="pref:notifications"),
            AppleUI.create_button("🎬 动画", callback_data="pref:animation")
        ],
        [
            AppleUI.create_button("📊 简洁模式", callback_data="pref:compact"),
            AppleUI.create_button("🔄 重置", callback_data="pref:reset")
        ],
        [
            AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
