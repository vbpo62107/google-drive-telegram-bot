"""
Apple 风格的设置界面
提供用户个性化设置和偏好管理
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot import LOGGER, SUDO_USERS, DOWNLOAD_DIRECTORY
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper import gDriveDB
import os


# 用户设置缓存（实际应用中应使用数据库）
user_settings = {}


def get_user_settings(user_id: int) -> dict:
    """
    获取用户设置
    """
    if user_id not in user_settings:
        user_settings[user_id] = {
            'theme': 'auto',  # auto, light, dark
            'language': 'zh-CN',  # zh-CN, en-US
            'notifications': True,
            'auto_delete': False,
            'upload_folder': 'root',
            'max_file_size': 10 * 1024 * 1024 * 1024,  # 10 GB
        }
    return user_settings[user_id]


def set_user_setting(user_id: int, key: str, value) -> None:
    """
    设置用户偏好
    """
    settings = get_user_settings(user_id)
    settings[key] = value
    user_settings[user_id] = settings
    LOGGER.info(f"User {user_id} updated setting {key} = {value}")


@Client.on_message(filters.command(["settings_apple", "sa"]) & filters.private, group=0)
async def settings_apple_handler(client: Client, message):
    """
    Apple 风格的设置主界面
    """
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    # 检查授权状态
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
            AppleUI.create_button("返回", callback_data="back_home", icon=AppleUI.ICONS["home"])
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^settings_gdrive$"))
async def settings_gdrive_callback(client: Client, callback_query: CallbackQuery):
    """
    Google Drive 设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    is_authorized = gDriveDB.is_authorized(user_id)
    
    if is_authorized:
        # 已授权，显示详细信息
        record = gDriveDB.search(user_id)
        device = record.device if record else "未知设备"
        
        text = AppleUI.format_message(
            title="Google Drive",
            icon=AppleUI.ICONS["gdrive"],
            content=(
                f"**连接状态**\n"
                f"✅ 已连接\n\n"
                f"**设备信息**\n"
                f"`{device}`\n\n"
                f"**上传文件夹**\n"
                f"{settings['upload_folder']}\n\n"
                f"**文件大小限制**\n"
                f"{settings['max_file_size'] // (1024**3)} GB"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("更改文件夹", callback_data="change_upload_folder", icon=AppleUI.ICONS["folder"])],
            [AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["delete"])],
            [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
        ])
    else:
        # 未授权，提示授权
        text = AppleUI.format_message(
            title="Google Drive",
            icon=AppleUI.ICONS["gdrive"],
            content=(
                "**连接状态**\n"
                "⚠️ 未连接\n\n"
                "连接 Google Drive 以使用上传功能\n\n"
                "授权后您可以：\n"
                "• 上传文件到 Drive\n"
                "• 搜索和管理文件\n"
                "• 克隆和分享文件"
            ),
            footer="🔒 您的数据安全受到保护"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
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
    
    current_theme = settings['theme']
    theme_emoji = {
        'auto': '🌓',
        'light': '☀️',
        'dark': '🌙'
    }
    
    text = AppleUI.format_message(
        title="外观设置",
        icon="🌓",
        content=(
            f"**当前主题**\n"
            f"{theme_emoji[current_theme]} {current_theme.title()}\n\n"
            f"**语言**\n"
            f"🌍 {settings['language']}\n\n"
            "选择您喜欢的外观主题"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "自动" + (" ✓" if current_theme == 'auto' else ""),
                callback_data="theme_auto",
                icon="🌓"
            ),
            AppleUI.create_button(
                "浅色" + (" ✓" if current_theme == 'light' else ""),
                callback_data="theme_light",
                icon="☀️"
            )
        ],
        [
            AppleUI.create_button(
                "深色" + (" ✓" if current_theme == 'dark' else ""),
                callback_data="theme_dark",
                icon="🌙"
            )
        ],
        [AppleUI.create_button("语言设置", callback_data="settings_language", icon="🌍")],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^theme_(auto|light|dark)$"))
async def theme_change_callback(client: Client, callback_query: CallbackQuery):
    """
    更改主题
    """
    user_id = callback_query.from_user.id
    theme = callback_query.data.split("_")[1]
    
    set_user_setting(user_id, 'theme', theme)
    
    await callback_query.answer(f"✅ 主题已切换到 {theme.title()}")
    
    # 刷新外观设置页面
    await settings_appearance_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_notifications$"))
async def settings_notifications_callback(client: Client, callback_query: CallbackQuery):
    """
    通知设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    text = AppleUI.format_message(
        title="通知设置",
        icon="🔔",
        content=(
            f"**推送通知**\n"
            f"{'✅ 开启' if settings['notifications'] else '⚠️ 关闭'}\n\n"
            "**通知类型**\n"
            "• 上传完成通知\n"
            "• 任务失败通知\n"
            "• 系统消息\n\n"
            "开启通知以及时了解任务状态"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "开启通知" if not settings['notifications'] else "关闭通知",
                callback_data="toggle_notifications",
                icon="🔔" if not settings['notifications'] else "🔕"
            )
        ],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^toggle_notifications$"))
async def toggle_notifications_callback(client: Client, callback_query: CallbackQuery):
    """
    切换通知状态
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    new_state = not settings['notifications']
    set_user_setting(user_id, 'notifications', new_state)
    
    await callback_query.answer(
        f"✅ 通知已{'开启' if new_state else '关闭'}"
    )
    
    # 刷新通知设置页面
    await settings_notifications_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^settings_advanced$"))
async def settings_advanced_callback(client: Client, callback_query: CallbackQuery):
    """
    高级设置
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    # 计算存储使用情况
    download_dir = DOWNLOAD_DIRECTORY
    total_size = 0
    if os.path.exists(download_dir):
        for dirpath, dirnames, filenames in os.walk(download_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    
    storage_mb = total_size / (1024 * 1024)
    
    text = AppleUI.format_message(
        title="高级设置",
        icon="⚙️",
        content=(
            f"**存储管理**\n"
            f"本地缓存: {storage_mb:.1f} MB\n\n"
            f"**自动删除**\n"
            f"{'✅ 开启' if settings['auto_delete'] else '⚠️ 关闭'}\n\n"
            f"**文件大小限制**\n"
            f"{settings['max_file_size'] // (1024**3)} GB\n\n"
            "高级功能配置"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "开启自动删除" if not settings['auto_delete'] else "关闭自动删除",
                callback_data="toggle_auto_delete",
                icon="🗑"
            )
        ],
        [AppleUI.create_button("清理缓存", callback_data="clear_cache", icon="🧹")],
        [AppleUI.create_button("文件大小限制", callback_data="set_file_limit", icon="📏")],
        [AppleUI.create_button("返回设置", callback_data="back_to_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^toggle_auto_delete$"))
async def toggle_auto_delete_callback(client: Client, callback_query: CallbackQuery):
    """
    切换自动删除
    """
    user_id = callback_query.from_user.id
    settings = get_user_settings(user_id)
    
    new_state = not settings['auto_delete']
    set_user_setting(user_id, 'auto_delete', new_state)
    
    await callback_query.answer(
        f"✅ 自动删除已{'开启' if new_state else '关闭'}"
    )
    
    # 刷新高级设置页面
    await settings_advanced_callback(client, callback_query)


@Client.on_callback_query(filters.regex(r"^clear_cache$"))
async def clear_cache_callback(client: Client, callback_query: CallbackQuery):
    """
    清理缓存
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 需要管理员权限", show_alert=True)
        return
    
    text = AppleUI.format_message(
        title="清理缓存",
        icon="🧹",
        content=(
            "确定要清理所有本地缓存吗？\n\n"
            "这将删除：\n"
            "• 所有临时下载文件\n"
            "• 上传缓存\n\n"
            "⚠️ 此操作不可撤销"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("确认清理", callback_data="confirm_clear_cache", icon="🗑")],
        [AppleUI.create_button("取消", callback_data="settings_advanced", icon=AppleUI.ICONS["cancel"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^confirm_clear_cache$"))
async def confirm_clear_cache_callback(client: Client, callback_query: CallbackQuery):
    """
    确认清理缓存
    """
    if callback_query.from_user.id not in SUDO_USERS:
        await callback_query.answer("⚠️ 需要管理员权限", show_alert=True)
        return
    
    try:
        # 清理下载目录
        download_dir = DOWNLOAD_DIRECTORY
        if os.path.exists(download_dir):
            import shutil
            for item in os.listdir(download_dir):
                item_path = os.path.join(download_dir, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        
        success = AppleUI.create_success_message(
            title="清理完成",
            message="缓存已成功清理"
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"],
            footer="💾 本地存储已释放"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("返回设置", callback_data="settings_advanced", icon=AppleUI.ICONS["back"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("✅ 清理完成")
        
    except Exception as e:
        LOGGER.exception(f"Failed to clear cache: {e}")
        await callback_query.answer("❌ 清理失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^back_to_settings$"))
async def back_to_settings_callback(client: Client, callback_query: CallbackQuery):
    """
    返回设置主页
    """
    # 模拟 /settings_apple 命令
    message = callback_query.message
    message.from_user = callback_query.from_user
    message.text = "/settings_apple"
    
    user_id = callback_query.from_user.id
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
            AppleUI.create_button("返回", callback_data="back_home", icon=AppleUI.ICONS["home"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
