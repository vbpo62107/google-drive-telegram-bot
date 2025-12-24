"""
Apple 风格的设置面板
提供集中化的设置管理界面
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.helpers.sql_helper.gDriveDB import is_authorized


@Client.on_message(filters.command(["settings_apple", "sa"]) & filters.private, group=0)
async def settings_apple_handler(client: Client, message):
    """
    Apple 风格的设置面板
    """
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的体验",
        content=(
            "选择下方选项进行配置"
        )
    )
    
    # 检查授权状态
    is_auth = is_authorized(str(message.from_user.id)) if message.from_user else False
    auth_status = "✅ 已授权" if is_auth else "❌ 未授权"
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                f"Google Drive {auth_status}",
                callback_data="settings_auth",
                icon=AppleUI.ICONS["gdrive"]
            )
        ],
        [
            AppleUI.create_button(
                "上传设置",
                callback_data="settings_upload",
                icon=AppleUI.ICONS["upload"]
            ),
            AppleUI.create_button(
                "文件管理",
                callback_data="settings_files",
                icon=AppleUI.ICONS["folder"]
            )
        ],
        [
            AppleUI.create_button(
                "快捷命令",
                callback_data="settings_commands",
                icon=AppleUI.ICONS["menu"]
            ),
            AppleUI.create_button(
                "关于",
                callback_data="show_about",
                icon=AppleUI.ICONS["info"]
            )
        ],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^settings_auth$"))
async def settings_auth_callback(client: Client, callback_query: CallbackQuery):
    """授权设置"""
    is_auth = is_authorized(str(callback_query.from_user.id))
    
    if is_auth:
        text = AppleUI.format_message(
            title="Google Drive 授权",
            icon=AppleUI.ICONS["success"],
            content=(
                "**当前状态**: ✅ 已授权\n\n"
                "您的 Google Drive 已成功连接\n\n"
                "可以使用以下功能：\n"
                "• 上传文件到 Drive\n"
                "• 搜索和管理文件\n"
                "• 克隆和删除文件"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["delete"])],
            [AppleUI.create_button("返回设置", callback_data="back_settings", icon=AppleUI.ICONS["back"])]
        ])
    else:
        text = AppleUI.format_message(
            title="Google Drive 授权",
            icon=AppleUI.ICONS["warning"],
            content=(
                "**当前状态**: ❌ 未授权\n\n"
                "您尚未连接 Google Drive\n\n"
                "授权后可以使用：\n"
                "• 上传文件到 Drive\n"
                "• 搜索和管理文件\n"
                "• 克隆和删除文件"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回设置", callback_data="back_settings", icon=AppleUI.ICONS["back"])]
        ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_upload$"))
async def settings_upload_callback(client: Client, callback_query: CallbackQuery):
    """上传设置"""
    text = AppleUI.format_message(
        title="上传设置",
        icon=AppleUI.ICONS["upload"],
        content=(
            "**可用功能**\n\n"
            "1. **镜像任务**\n"
            "   `/mirror_apple <URL>` - 下载并上传到 Drive\n\n"
            "2. **直接上传**\n"
            "   直接发送文件给 bot\n\n"
            "3. **设置默认文件夹**\n"
            "   `/setfolder` - 选择上传目标位置\n\n"
            "💡 提示：使用 `/ma` 作为 mirror_apple 的简写"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("创建任务", callback_data="create_mirror", icon=AppleUI.ICONS["mirroring"]),
            AppleUI.create_button("设置文件夹", callback_data="set_folder", icon=AppleUI.ICONS["folder"])
        ],
        [AppleUI.create_button("返回设置", callback_data="back_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_files$"))
async def settings_files_callback(client: Client, callback_query: CallbackQuery):
    """文件管理设置"""
    text = AppleUI.format_message(
        title="文件管理",
        icon=AppleUI.ICONS["folder"],
        content=(
            "**可用功能**\n\n"
            "1. **克隆文件**\n"
            "   `/clone_apple <Drive链接>` - 克隆到您的 Drive\n\n"
            "2. **删除文件**\n"
            "   `/delete_apple <Drive链接>` - 删除文件\n\n"
            "3. **搜索文件**\n"
            "   `/searchdrive <关键词>` - 搜索 Drive\n\n"
            "4. **清空回收站**\n"
            "   `/emptytrash_apple` - 永久删除\n\n"
            "💡 提示：使用简写命令更快捷（/ca, /da, /eta）"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("克隆文件", callback_data="clone_file", icon=AppleUI.ICONS["copy"]),
            AppleUI.create_button("删除文件", callback_data="delete_file", icon=AppleUI.ICONS["delete"])
        ],
        [
            AppleUI.create_button("搜索文件", callback_data="search_files", icon=AppleUI.ICONS["search"]),
            AppleUI.create_button("清空回收站", callback_data="empty_trash", icon="🗑")
        ],
        [AppleUI.create_button("返回设置", callback_data="back_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^settings_commands$"))
async def settings_commands_callback(client: Client, callback_query: CallbackQuery):
    """快捷命令设置"""
    text = AppleUI.format_message(
        title="快捷命令",
        icon=AppleUI.ICONS["menu"],
        content=(
            "**Apple 风格命令快速参考**\n\n"
            "**基础功能**\n"
            "`/start` - 欢迎页面\n"
            "`/help` - 帮助信息\n"
            "`/sa` - 设置面板\n\n"
            "**授权管理**\n"
            "`/aa` - Google Drive 授权\n"
            "`/ra` - 撤销授权\n\n"
            "**文件操作**\n"
            "`/ma <URL>` - 镜像任务\n"
            "`/ca <链接>` - 克隆文件\n"
            "`/da <链接>` - 删除文件\n"
            "`/eta` - 清空回收站\n\n"
            "💡 所有命令都支持完整名称和简写"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("复制全部命令", callback_data="copy_commands", icon=AppleUI.ICONS["copy"])],
        [AppleUI.create_button("返回设置", callback_data="back_settings", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^copy_commands$"))
async def copy_commands_callback(client: Client, callback_query: CallbackQuery):
    """复制所有命令"""
    commands_text = (
        "/start - 欢迎页面\n"
        "/help - 帮助信息\n"
        "/sa - 设置面板\n"
        "/aa - Google Drive 授权\n"
        "/ra - 撤销授权\n"
        "/ma <URL> - 镜像任务\n"
        "/ca <链接> - 克隆文件\n"
        "/da <链接> - 删除文件\n"
        "/eta - 清空回收站"
    )
    
    await callback_query.answer("✅ 命令列表已复制，请查看下方消息", show_alert=False)
    await client.send_message(
        callback_query.from_user.id,
        f"**快捷命令列表**\n\n{commands_text}",
        parse_mode="Markdown"
    )


@Client.on_callback_query(filters.regex(r"^back_settings$"))
async def back_settings_callback(client: Client, callback_query: CallbackQuery):
    """返回设置主页面"""
    text = AppleUI.format_message(
        title="设置",
        icon=AppleUI.ICONS["settings"],
        subtitle="自定义您的体验",
        content="选择下方选项进行配置"
    )
    
    # 检查授权状态
    is_auth = is_authorized(str(callback_query.from_user.id))
    auth_status = "✅ 已授权" if is_auth else "❌ 未授权"
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                f"Google Drive {auth_status}",
                callback_data="settings_auth",
                icon=AppleUI.ICONS["gdrive"]
            )
        ],
        [
            AppleUI.create_button(
                "上传设置",
                callback_data="settings_upload",
                icon=AppleUI.ICONS["upload"]
            ),
            AppleUI.create_button(
                "文件管理",
                callback_data="settings_files",
                icon=AppleUI.ICONS["folder"]
            )
        ],
        [
            AppleUI.create_button(
                "快捷命令",
                callback_data="settings_commands",
                icon=AppleUI.ICONS["menu"]
            ),
            AppleUI.create_button(
                "关于",
                callback_data="show_about",
                icon=AppleUI.ICONS["info"]
            )
        ],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# 快捷操作回调

@Client.on_callback_query(filters.regex(r"^create_mirror$"))
async def create_mirror_callback(client: Client, callback_query: CallbackQuery):
    """创建镜像任务引导"""
    text = AppleUI.format_message(
        title="创建镜像任务",
        icon=AppleUI.ICONS["mirroring"],
        content=(
            "**使用以下命令创建任务：**\n\n"
            "`/mirror_apple <URL>`\n\n"
            "或使用简写：\n"
            "`/ma <URL>`\n\n"
            "💡 示例：\n"
            "`/ma https://example.com/file.zip`"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_upload", icon=AppleUI.ICONS["back"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^set_folder$"))
async def set_folder_callback(client: Client, callback_query: CallbackQuery):
    """设置文件夹引导"""
    text = AppleUI.format_message(
        title="设置上传文件夹",
        icon=AppleUI.ICONS["folder"],
        content=(
            "**使用以下命令设置：**\n\n"
            "`/setfolder`\n\n"
            "然后按照提示选择文件夹"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_upload", icon=AppleUI.ICONS["back"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^clone_file$"))
async def clone_file_callback(client: Client, callback_query: CallbackQuery):
    """克隆文件引导"""
    text = AppleUI.format_message(
        title="克隆 Drive 文件",
        icon=AppleUI.ICONS["copy"],
        content=(
            "**使用以下命令克隆：**\n\n"
            "`/clone_apple <Drive链接>`\n\n"
            "或使用简写：\n"
            "`/ca <Drive链接>`"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_files", icon=AppleUI.ICONS["back"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^delete_file$"))
async def delete_file_callback(client: Client, callback_query: CallbackQuery):
    """删除文件引导"""
    text = AppleUI.format_message(
        title="删除 Drive 文件",
        icon=AppleUI.ICONS["delete"],
        content=(
            "**使用以下命令删除：**\n\n"
            "`/delete_apple <Drive链接>`\n\n"
            "或使用简写：\n"
            "`/da <Drive链接>`\n\n"
            "⚠️ 注意：文件将移入回收站"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_files", icon=AppleUI.ICONS["back"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^search_files$"))
async def search_files_callback(client: Client, callback_query: CallbackQuery):
    """搜索文件引导"""
    text = AppleUI.format_message(
        title="搜索 Drive 文件",
        icon=AppleUI.ICONS["search"],
        content=(
            "**使用以下命令搜索：**\n\n"
            "`/searchdrive <关键词>`\n\n"
            "或使用简写：\n"
            "`/sdrive <关键词>`"
        )
    )
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回", callback_data="settings_files", icon=AppleUI.ICONS["back"])]
    ])
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()
