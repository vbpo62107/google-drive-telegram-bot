"""
Apple 风格的设置界面
提供用户个性化配置选项
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import LOGGER, SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper import gDriveDB


# 用户设置存储（实际应该使用数据库）
user_settings = {}


def get_user_settings(user_id: int) -> dict:
    """
    获取用户设置
    """
    if user_id not in user_settings:
        user_settings[user_id] = {
            "language": "zh",  # 中文
            "notifications": True,
            "auto_delete": False,
            "upload_folder": "root",
            "file_size_limit": 2 * 1024 * 1024 * 1024,  # 2GB
            "theme": "auto",  # auto, light, dark
        }
    return user_settings[user_id]


def set_user_setting(user_id: int, key: str, value) -> None:
    """
    设置用户配置
    """
    settings = get_user_settings(user_id)
    settings[key] = value
    LOGGER.info(f"User {user_id} updated setting {key} = {value}")


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


@Client.on_message(filters.command(["settings_apple", "sa"]) & filters.private, group=0)
async def settings_apple_handler(client: Client, message):
    """
    Apple 风格的设置主页面
    """
    user_id = message.from_user.id
    await show_settings_main(client, message, user_id)


async def show_settings_main(client: Client, message, user_id: int):
    """
    显示设置主页面
    """
    settings = get_user_settings(user_id)
    
    # 检查授权状态
    is_authorized = False
    try:
        is_authorized = gDriveDB.is_authorized(user_id)
    except:
        pass
    
    auth_status = "✅ 已连接" if is_authorized else "❌ 未连接"
    
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的使用体验",
        content=(
            f"**账户状态**\n"
            f"Google Drive: {auth_status}\n\n"
            f"**当前配置**\n"
            f"• 语言: 简体中文\n"
            f"• 主题: {'自动' if settings['theme'] == 'auto' else settings['theme']}\n"
            f"• 通知: {'开启' if settings['notifications'] else '关闭'}\n\n"
            f"选择下方选项进行配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("Google Drive", callback_data="settings_drive", icon=AppleUI.ICONS["gdrive"])],
        [
            AppleUI.create_button("上传设置", callback_data="settings_upload", icon=AppleUI.ICONS["upload"]),
            AppleUI.create_button("通知设置", callback_data="settings_notifications", icon="🔔")
        ],
        [
            AppleUI.create_button("外观", callback_data="settings_appearance", icon="🎨"),
            AppleUI.create_button("语言", callback_data="settings_language", icon="🌐")
        ],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^settings_drive$"))
async def settings_drive_callback(client: Client, callback_query: CallbackQuery):
    """
    Google Drive 设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    # 检查授权状态
    is_authorized = False
    device_name = "未知设备"
    try:
        record = gDriveDB.search(user_id)
        if record:
            is_authorized = True
            device_name = record.device or "telegram"
    except:
        pass
    
    if is_authorized:
        text = AppleUI.format_message(
            title="Google Drive 设置",
            icon=AppleUI.ICONS["gdrive"],
            content=(
                "**连接状态**\n"
                "✅ 已连接\n\n"
                f"**设备名称**\n"
                f"`{device_name}`\n\n"
                f"**默认上传文件夹**\n"
                f"{settings['upload_folder']}\n\n"
                "您可以管理授权或更改上传位置"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("更改上传文件夹", callback_data="change_upload_folder", icon=AppleUI.ICONS["folder"])],
            [AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["delete"])],
            [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
        ])
    else:
        text = AppleUI.format_message(
            title="Google Drive 设置",
            icon=AppleUI.ICONS["gdrive"],
            content=(
                "**连接状态**\n"
                "❌ 未连接\n\n"
                "连接 Google Drive 后即可使用：\n"
                "• 上传文件到云端\n"
                "• 管理和搜索文件\n"
                "• 克隆和分享文件\n\n"
                "点击下方按钮开始授权"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
        ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_upload$"))
async def settings_upload_callback(client: Client, callback_query: CallbackQuery):
    """
    上传设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    size_limit = format_file_size(settings['file_size_limit'])
    auto_delete = "开启" if settings['auto_delete'] else "关闭"
    
    text = AppleUI.format_message(
        title="上传设置",
        icon=AppleUI.ICONS["upload"],
        content=(
            f"**文件大小限制**\n"
            f"{size_limit}\n\n"
            f"**自动删除本地文件**\n"
            f"{auto_delete}\n\n"
            "调整这些设置以优化上传体验"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("修改大小限制", callback_data="change_size_limit", icon="📏")],
        [
            AppleUI.create_button(
                f"自动删除: {auto_delete}",
                callback_data="toggle_auto_delete",
                icon="🗑" if settings['auto_delete'] else "💾"
            )
        ],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_notifications$"))
async def settings_notifications_callback(client: Client, callback_query: CallbackQuery):
    """
    通知设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    notifications = "开启" if settings['notifications'] else "关闭"
    
    text = AppleUI.format_message(
        title="通知设置",
        icon="🔔",
        content=(
            f"**任务完成通知**\n"
            f"{notifications}\n\n"
            "开启后将在以下情况收到通知：\n"
            "• 文件上传完成\n"
            "• 镜像任务完成\n"
            "• 发生错误时\n\n"
            f"当前状态: {'您将收到通知' if settings['notifications'] else '不会收到通知'}"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                f"通知: {notifications}",
                callback_data="toggle_notifications",
                icon="🔔" if settings['notifications'] else "🔕"
            )
        ],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_appearance$"))
async def settings_appearance_callback(client: Client, callback_query: CallbackQuery):
    """
    外观设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    theme_names = {
        "auto": "跟随系统",
        "light": "浅色模式",
        "dark": "深色模式"
    }
    current_theme = theme_names.get(settings['theme'], "跟随系统")
    
    text = AppleUI.format_message(
        title="外观",
        icon="🎨",
        content=(
            f"**主题**\n"
            f"{current_theme}\n\n"
            "选择您喜欢的界面主题：\n"
            "• 跟随系统 - 自动适应设备设置\n"
            "• 浅色模式 - 明亮清新\n"
            "• 深色模式 - 护眼舒适\n\n"
            "💡 主题仅影响 emoji 和文本样式"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "跟随系统",
                callback_data="theme_auto",
                icon="✓" if settings['theme'] == 'auto' else "○"
            )
        ],
        [
            AppleUI.create_button(
                "浅色",
                callback_data="theme_light",
                icon="✓" if settings['theme'] == 'light' else "○"
            ),
            AppleUI.create_button(
                "深色",
                callback_data="theme_dark",
                icon="✓" if settings['theme'] == 'dark' else "○"
            )
        ],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_language$"))
async def settings_language_callback(client: Client, callback_query: CallbackQuery):
    """
    语言设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    text = AppleUI.format_message(
        title="语言设置",
        icon="🌐",
        content=(
            "**当前语言**\n"
            "简体中文\n\n"
            "选择您喜欢的界面语言：\n\n"
            "🚧 更多语言即将推出"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("✓ 简体中文", callback_data="lang_zh", icon="🇨🇳")],
        [AppleUI.create_button("○ English (即将推出)", callback_data="lang_en_soon", icon="🇺🇸")],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# 设置切换回调

@Client.on_callback_query(filters.regex(r"^toggle_notifications$"))
async def toggle_notifications_callback(client: Client, callback_query: CallbackQuery):
    """
    切换通知开关
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    # 切换状态
    settings['notifications'] = not settings['notifications']
    set_user_setting(user_id, 'notifications', settings['notifications'])
    
    # 刷新页面
    await settings_notifications_callback(client, callback_query)
    
    status = "已开启" if settings['notifications'] else "已关闭"
    await callback_query.answer(f"通知{status}")


@Client.on_callback_query(filters.regex(r"^toggle_auto_delete$"))
async def toggle_auto_delete_callback(client: Client, callback_query: CallbackQuery):
    """
    切换自动删除开关
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    settings['auto_delete'] = not settings['auto_delete']
    set_user_setting(user_id, 'auto_delete', settings['auto_delete'])
    
    await settings_upload_callback(client, callback_query)
    
    status = "已开启" if settings['auto_delete'] else "已关闭"
    await callback_query.answer(f"自动删除{status}")


@Client.on_callback_query(filters.regex(r"^theme_(auto|light|dark)$"))
async def theme_callback(client: Client, callback_query: CallbackQuery):
    """
    切换主题
    """
    user_id = callback_query.from_user.id
    theme = callback_query.data.split("_")[1]
    
    set_user_setting(user_id, 'theme', theme)
    
    await settings_appearance_callback(client, callback_query)
    
    theme_names = {"auto": "跟随系统", "light": "浅色", "dark": "深色"}
    await callback_query.answer(f"已切换到{theme_names[theme]}")


@Client.on_callback_query(filters.regex(r"^back_to_settings$"))
async def back_to_settings_callback(client: Client, callback_query: CallbackQuery):
    """
    返回设置主页
    """
    user_id = callback_query.from_user.id
    await show_settings_main(client, callback_query.message, user_id)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^change_upload_folder$"))
async def change_upload_folder_callback(client: Client, callback_query: CallbackQuery):
    """
    更改上传文件夹（占位）
    """
    text = AppleUI.format_message(
        title="更改上传文件夹",
        icon=AppleUI.ICONS["folder"],
        content=(
            "请使用 `/setfolder` 命令选择\n"
            "Google Drive 中的上传位置\n\n"
            "💡 提示：此功能将在后续版本中\n"
            "集成到设置界面"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_drive", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^change_size_limit$"))
async def change_size_limit_callback(client: Client, callback_query: CallbackQuery):
    """
    更改文件大小限制
    """
    user_id = callback_query.from_user.id
    
    text = AppleUI.format_message(
        title="文件大小限制",
        icon="📏",
        content=(
            "选择最大文件大小限制：\n\n"
            "💡 提示：较大的限制可能导致\n"
            "上传时间较长"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("500 MB", callback_data="size_500mb", icon="○")],
        [AppleUI.create_button("1 GB", callback_data="size_1gb", icon="○")],
        [AppleUI.create_button("2 GB (推荐)", callback_data="size_2gb", icon="✓")],
        [AppleUI.create_button("5 GB", callback_data="size_5gb", icon="○")],
        [AppleUI.create_button("返回", callback_data="settings_upload", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^size_(500mb|1gb|2gb|5gb)$"))
async def size_limit_callback(client: Client, callback_query: CallbackQuery):
    """
    设置文件大小限制
    """
    user_id = callback_query.from_user.id
    size_key = callback_query.data.split("_")[1]
    
    sizes = {
        "500mb": 500 * 1024 * 1024,
        "1gb": 1024 * 1024 * 1024,
        "2gb": 2 * 1024 * 1024 * 1024,
        "5gb": 5 * 1024 * 1024 * 1024,
    }
    
    set_user_setting(user_id, 'file_size_limit', sizes[size_key])
    
    await settings_upload_callback(client, callback_query)
    await callback_query.answer(f"已设置为 {format_file_size(sizes[size_key])}")
