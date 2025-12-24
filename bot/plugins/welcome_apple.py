"""
Apple 风格的欢迎和帮助页面
重构 /start 和 /help 命令以符合 Apple 设计语言
"""

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot import SUPPORT_CHAT_LINK
from bot.ui_apple_style import AppleUI


@Client.on_message(filters.private & filters.incoming & filters.command(["start"]), group=1)
async def start_apple(client: Client, message):
    """
    Apple 风格的欢迎消息
    """
    user_name = message.from_user.first_name or "用户"
    
    text = AppleUI.format_message(
        title="Google Drive Uploader",
        icon="🎉",
        subtitle=f"欢迎，{user_name}!",
        content=(
            "轻松上传文件到 Google Drive\n\n"
            "__主要功能__\n"
            "• 上传 Telegram 文件\n"
            "• 支持直链下载\n"
            "• 团队盘支持\n"
            "• 文件镜像管理\n"
            "• 智能搜索与管理\n\n"
            "点击下方按钮开始使用"
        )
    )
    
    # Apple 风格的按钮布局 - 简洁且有层次
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("开始使用", callback_data="get_started", icon=AppleUI.ICONS["upload"])],
        [
            AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"]),
            AppleUI.create_button("关于", callback_data="show_about", icon=AppleUI.ICONS["info"])
        ],
        [AppleUI.create_button("支持群组", url=SUPPORT_CHAT_LINK, icon="💬")]
    ])
    
    await message.reply_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


@Client.on_message(filters.private & filters.incoming & filters.command(["help"]), group=1)
async def help_apple(client: Client, message):
    """
    Apple 风格的帮助页面
    """
    await show_help_page(client, message)


async def show_help_page(client: Client, message, page: int = 1):
    """
    显示帮助页面
    """
    if page == 1:
        # 第一页：基本命令
        text = AppleUI.format_message(
            title="命令帮助",
            icon=AppleUI.ICONS["help"],
            subtitle="基本命令",
            content=(
                "`/start` - 显示欢迎消息\n"
                "`/help` - 显示帮助信息\n"
                "`/auth` - 授权 Google Drive\n"
                "`/revoke` - 撤销授权\n"
                "`/setfolder` - 设置上传文件夹\n\n"
            ),
            footer="💡 提示：点击命令可快速复制"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("下一页", callback_data="help_page_2", icon=AppleUI.ICONS["forward"])],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
    elif page == 2:
        # 第二页：文件操作
        text = AppleUI.format_message(
            title="命令帮助",
            icon=AppleUI.ICONS["help"],
            subtitle="文件操作",
            content=(
                "`/mirror` <链接> - 镜像文件到 Drive\n"
                "`/clone` <Drive 链接> - 克隆 Drive 文件\n"
                "`/delete` <Drive 链接> - 删除文件\n"
                "`/emptytrash` - 清空回收站\n\n"
            ),
            footer="💡 提示：支持批量操作"
        )
        
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("上一页", callback_data="help_page_1", icon=AppleUI.ICONS["back"]),
                AppleUI.create_button("下一页", callback_data="help_page_3", icon=AppleUI.ICONS["forward"])
            ],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
    else:  # page == 3
        # 第三页：搜索和监控
        text = AppleUI.format_message(
            title="命令帮助",
            icon=AppleUI.ICONS["help"],
            subtitle="搜索与监控",
            content=(
                "`/searchdrive` <关键词> - 搜索 Drive 文件\n"
                "`/listdrive` - 列出 Drive 文件\n"
                "`/addmonitor` - 添加频道监控\n"
                "`/listmonitor` - 查看监控列表\n"
                "`/togglemonitor` - 切换监控状态\n"
                "`/delmonitor` - 删除监控\n\n"
            ),
            footer="🔥 需要帮助？加入支持群组！"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("上一页", callback_data="help_page_2", icon=AppleUI.ICONS["back"])],
            [
                AppleUI.create_button("支持群组", url=SUPPORT_CHAT_LINK, icon="💬"),
                AppleUI.create_button("问题反馈", url="https://github.com/vbpo62107/google-drive-telegram-bot/issues", icon="🐛")
            ],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
    
    # 如果是从回调调用，编辑消息；否则发送新消息
    if hasattr(message, 'edit_text'):
        await message.edit_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )


@Client.on_callback_query(filters.regex(r"^help_page_(\d+)$"))
async def help_page_callback(client: Client, callback_query: CallbackQuery):
    """
    处理帮助页面的翻页回调
    """
    page = int(callback_query.data.split("_")[-1])
    await show_help_page(client, callback_query.message, page)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^get_started$"))
async def get_started_callback(client: Client, callback_query: CallbackQuery):
    """
    处理“开始使用”按钮
    """
    text = AppleUI.format_message(
        title="快速开始",
        icon="🚀",
        content=(
            "**第一步：授权 Google Drive**\n"
            "使用 `/auth` 命令连接您的 Google Drive 账户\n\n"
            "**第二步：设置上传文件夹**\n"
            "使用 `/setfolder` 命令选择默认上传位置\n\n"
            "**第三步：开始上传**\n"
            "直接发送文件或使用 `/mirror` 命令\n\n"
            "💡 就这么简单！"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])],
        [AppleUI.create_button("查看详细帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^show_help$"))
async def show_help_callback(client: Client, callback_query: CallbackQuery):
    """
    处理“帮助”按钮
    """
    await show_help_page(client, callback_query.message, page=1)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^show_about$"))
async def show_about_callback(client: Client, callback_query: CallbackQuery):
    """
    处理“关于”按钮
    """
    text = AppleUI.format_message(
        title="关于本 Bot",
        icon=AppleUI.ICONS["info"],
        content=(
            "**Google Drive Uploader Bot**\n"
            "Version 1.0.0\n\n"
            "一个功能强大的 Telegram 机器人，用于管理\n"
            "您的 Google Drive 文件。\n\n"
            "__技术栈__\n"
            "• Python 3.9+\n"
            "• Pyrogram\n"
            "• Google Drive API\n\n"
            "__开源许可__\n"
            "GPL-3.0 License"
        ),
        footer="💙 感谢使用！"
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("GitHub", url="https://github.com/vbpo62107/google-drive-telegram-bot", icon="🐱"),
            AppleUI.create_button("支持群组", url=SUPPORT_CHAT_LINK, icon="💬")
        ],
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^back_home$"))
async def back_home_callback(client: Client, callback_query: CallbackQuery):
    """
    处理“返回主页”按钮
    """
    user_name = callback_query.from_user.first_name or "用户"
    
    text = AppleUI.format_message(
        title="Google Drive Uploader",
        icon="🎉",
        subtitle=f"欢迎，{user_name}!",
        content=(
            "轻松上传文件到 Google Drive\n\n"
            "__主要功能__\n"
            "• 上传 Telegram 文件\n"
            "• 支持直链下载\n"
            "• 团队盘支持\n"
            "• 文件镜像管理\n"
            "• 智能搜索与管理\n\n"
            "点击下方按钮开始使用"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("开始使用", callback_data="get_started", icon=AppleUI.ICONS["upload"])],
        [
            AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"]),
            AppleUI.create_button("关于", callback_data="show_about", icon=AppleUI.ICONS["info"])
        ],
        [AppleUI.create_button("支持群组", url=SUPPORT_CHAT_LINK, icon="💬")]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer("已返回主页")


@Client.on_callback_query(filters.regex(r"^auth_now$"))
async def auth_now_callback(client: Client, callback_query: CallbackQuery):
    """
    处理“立即授权”按钮
    """
    text = AppleUI.format_message(
        title="Google Drive 授权",
        icon=AppleUI.ICONS["auth"],
        content=(
            "请使用以下命令开始授权：\n\n"
            "`/auth`\n\n"
            "您将收到一个 Google 授权链接。\n"
            "点击链接并完成授权流程。\n\n"
            "🔒 您的数据安全是我们的首要任务"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("了解更多", callback_data="show_help", icon=AppleUI.ICONS["help"])],
        [AppleUI.create_button("返回", callback_data="back_home", icon=AppleUI.ICONS["back"])]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()
