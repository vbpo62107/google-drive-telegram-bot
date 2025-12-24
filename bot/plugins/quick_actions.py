"""
快捷操作功能
提供常用操作的快速访问入口
支持自定义快捷键和模板
"""

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from bot import SUDO_USERS
from bot.ui_apple_style import AppleUI
from bot.ui_animations import UIAnimation, show_loading


class QuickActions:
    """快捷操作类"""
    
    # 快捷操作模板
    TEMPLATES = {
        "quick_upload": {
            "title": "快速上传",
            "icon": AppleUI.ICONS["upload"],
            "description": "直接发送文件到默认文件夹",
            "command": "/mirror_apple",
            "category": "文件操作"
        },
        "quick_search": {
            "title": "快速搜索",
            "icon": AppleUI.ICONS["search"],
            "description": "搜索 Google Drive 文件",
            "command": "/searchdrive",
            "category": "Drive 管理"
        },
        "quick_list": {
            "title": "查看文件",
            "icon": AppleUI.ICONS["folder"],
            "description": "列出 Drive 文件夹内容",
            "command": "/listdrive",
            "category": "Drive 管理"
        },
        "quick_auth": {
            "title": "快速授权",
            "icon": AppleUI.ICONS["auth"],
            "description": "连接 Google Drive",
            "command": "/auth_apple",
            "category": "设置"
        },
        "quick_help": {
            "title": "获取帮助",
            "icon": AppleUI.ICONS["help"],
            "description": "查看使用指南",
            "command": "/help",
            "category": "帮助"
        }
    }
    
    @staticmethod
    def get_category_actions(category: str) -> list:
        """获取指定分类的快捷操作"""
        return [
            (key, action) 
            for key, action in QuickActions.TEMPLATES.items()
            if action["category"] == category
        ]
    
    @staticmethod
    def get_all_categories() -> list:
        """获取所有分类"""
        categories = set()
        for action in QuickActions.TEMPLATES.values():
            categories.add(action["category"])
        return sorted(list(categories))


@Client.on_message(filters.command(["quick", "q"]) & filters.private)
async def quick_actions_menu(client: Client, message):
    """
    快捷操作菜单
    使用: /quick 或 /q
    """
    text = AppleUI.format_message(
        title="快捷操作",
        icon="⚡",
        subtitle="选择常用功能快速访问",
        content="点击下方按钮快速执行操作"
    )
    
    # 按分类组织按钮
    keyboard_rows = []
    
    # 文件操作
    file_actions = QuickActions.get_category_actions("文件操作")
    if file_actions:
        row = []
        for key, action in file_actions:
            row.append(AppleUI.create_button(
                action["title"],
                callback_data=f"qa:{key}",
                icon=action["icon"]
            ))
        keyboard_rows.append(row)
    
    # Drive 管理
    drive_actions = QuickActions.get_category_actions("Drive 管理")
    if drive_actions:
        row = []
        for key, action in drive_actions[:2]:  # 最多2个按钮一行
            row.append(AppleUI.create_button(
                action["title"],
                callback_data=f"qa:{key}",
                icon=action["icon"]
            ))
        keyboard_rows.append(row)
    
    # 设置和帮助
    other_row = []
    for category in ["设置", "帮助"]:
        actions = QuickActions.get_category_actions(category)
        for key, action in actions:
            other_row.append(AppleUI.create_button(
                action["title"],
                callback_data=f"qa:{key}",
                icon=action["icon"]
            ))
    if other_row:
        keyboard_rows.append(other_row)
    
    # 返回按钮
    keyboard_rows.append([
        AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^qa:"))
async def handle_quick_action(client: Client, callback_query: CallbackQuery):
    """处理快捷操作回调"""
    action_key = callback_query.data.replace("qa:", "")
    action = QuickActions.TEMPLATES.get(action_key)
    
    if not action:
        await callback_query.answer("⚠️ 操作不存在", show_alert=True)
        return
    
    # 显示加载动画
    loading_text = AppleUI.format_message(
        title="正在启动",
        icon=AppleUI.ICONS["processing"],
        content=f"{action['icon']} {action['title']}..."
    )
    
    await callback_query.message.edit_text(loading_text)
    await callback_query.answer(f"⚡ {action['title']}")
    
    # 模拟加载
    await show_loading(callback_query.message, action['title'], 1.5)
    
    # 显示操作提示
    text = AppleUI.format_message(
        title=action['title'],
        icon=action['icon'],
        content=(
            f"{action['description']}\n\n"
            f"**使用命令**\n`{action['command']}`\n\n"
            "💡 请按照命令格式输入内容"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "返回菜单",
                callback_data="show_quick_menu",
                icon=AppleUI.ICONS["back"]
            ),
            AppleUI.create_button(
                "帮助",
                callback_data="show_help",
                icon=AppleUI.ICONS["help"]
            )
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^show_quick_menu$"))
async def show_quick_menu_callback(client: Client, callback_query: CallbackQuery):
    """显示快捷菜单回调"""
    text = AppleUI.format_message(
        title="快捷操作",
        icon="⚡",
        subtitle="选择常用功能快速访问",
        content="点击下方按钮快速执行操作"
    )
    
    keyboard_rows = []
    
    # 重建按钮布局
    categories = ["文件操作", "Drive 管理", "设置", "帮助"]
    
    for category in categories:
        actions = QuickActions.get_category_actions(category)
        if actions:
            row = []
            for key, action in actions[:2]:
                row.append(AppleUI.create_button(
                    action["title"],
                    callback_data=f"qa:{key}",
                    icon=action["icon"]
                ))
            keyboard_rows.append(row)
    
    keyboard_rows.append([
        AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )
    ])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# Inline Query 支持快速搜索
@Client.on_inline_query()
async def inline_query_handler(client: Client, inline_query: InlineQuery):
    """
    Inline Query 处理器
    用户可以在任何聊天中输入 @bot_username <query> 来使用
    """
    query = inline_query.query.lower().strip()
    
    results = []
    
    # 如果查询为空，显示所有快捷操作
    if not query:
        for key, action in QuickActions.TEMPLATES.items():
            results.append(
                InlineQueryResultArticle(
                    title=f"{action['icon']} {action['title']}",
                    description=action['description'],
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"{action['icon']} **{action['title']}**\n\n"
                            f"{action['description']}\n\n"
                            f"使用命令: `{action['command']}`"
                        )
                    ),
                    thumb_url="https://img.icons8.com/fluency/48/000000/google-drive.png"
                )
            )
    else:
        # 根据查询过滤结果
        for key, action in QuickActions.TEMPLATES.items():
            if (query in action['title'].lower() or 
                query in action['description'].lower() or
                query in action['command'].lower()):
                
                results.append(
                    InlineQueryResultArticle(
                        title=f"{action['icon']} {action['title']}",
                        description=action['description'],
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"{action['icon']} **{action['title']}**\n\n"
                                f"{action['description']}\n\n"
                                f"使用命令: `{action['command']}`"
                            )
                        ),
                        thumb_url="https://img.icons8.com/fluency/48/000000/google-drive.png"
                    )
                )
    
    # 添加帮助项
    if not query or "help" in query:
        results.append(
            InlineQueryResultArticle(
                title="❓ 帮助文档",
                description="查看完整的使用指南",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "❓ **快捷操作帮助**\n\n"
                        "使用 `/quick` 或 `/q` 命令访问快捷菜单\n\n"
                        "**Inline 模式**\n"
                        "在任何聊天中输入 `@bot_username <关键词>` 来搜索功能"
                    )
                ),
                thumb_url="https://img.icons8.com/fluency/48/000000/help.png"
            )
        )
    
    try:
        await inline_query.answer(
            results=results[:50],  # 最多返回 50 个结果
            cache_time=300,  # 缓存 5 分钟
            is_personal=True
        )
    except Exception as e:
        # 如果 inline query 失败，静默失败
        pass


@Client.on_message(filters.command(["shortcuts"]) & filters.private)
async def show_shortcuts_guide(client: Client, message):
    """
    显示快捷键指南
    """
    text = AppleUI.format_message(
        title="快捷键指南",
        icon="⌨️",
        content=(
            "**基本快捷键**\n"
            "`/q` - 快捷操作菜单\n"
            "`/ma` - 快速镜像\n"
            "`/aa` - 快速授权\n"
            "`/ra` - 快速撤销\n\n"
            "**Inline 模式**\n"
            "在任何聊天中输入:\n"
            "`@bot_username` - 显示所有功能\n"
            "`@bot_username upload` - 搜索上传相关\n"
            "`@bot_username search` - 搜索搜索功能\n\n"
            "💡 使用 Inline 模式可以在任何聊天中快速分享功能"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "尝试快捷菜单",
            callback_data="show_quick_menu",
            icon="⚡"
        )],
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)
