"""
Apple 风格的文件操作命令
重构 /clone, /delete, /emptytrash 命令以符合 Apple 设计语言
"""

import asyncio

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper.gDriveDB import is_authorized
from bot.helpers.utils import CustomFilters
from bot.modules.drive_helper import (
    DriveAccessError,
    drive_error_message,
    get_drive_instance,
)
from bot.ui_apple_style import AppleUI


async def clone_handler(client, message):
    """
    Apple 风格的文件克隆命令
    """
    # 权限检查
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = f"{error['title']}\n\n{error['message']}"
        await client.send_message(message.chat.id, text)
        return
    
    # 授权检查
    if not is_authorized(str(message.from_user.id)):
        text = AppleUI.format_message(
            title="未授权",
            icon=AppleUI.ICONS["warning"],
            content=(
                "您需要先授权 Google Drive 才能使用此功能。\n\n"
                "请使用 `/auth` 命令完成授权。"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "立即授权",
                callback_data="auth_now",
                icon=AppleUI.ICONS["auth"]
            )]
        ])
        
        await client.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard
        )
        return
    
    # 检查参数
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) <= 1 or not parts[1].strip():
        text = AppleUI.format_message(
            title="缺少参数",
            icon=AppleUI.ICONS["warning"],
            content=(
                "请提供要克隆的 Google Drive 链接。\n\n"
                f"__使用方法__\n"
                f"`/{BotCommands.Clone[0]} <Drive 链接>`\n\n"
                "__示例__\n"
                f"`/{BotCommands.Clone[0]} https://drive.google.com/file/d/xxxxx`"
            )
        )
        await client.send_message(message.chat.id, text)
        return
    
    link = parts[1].strip()
    
    # 获取 Drive 实例
    try:
        drive = await get_drive_instance(str(message.from_user.id))
    except DriveAccessError as exc:
        error_msg = drive_error_message(exc.code)
        await client.send_message(message.chat.id, error_msg)
        return
    except Exception as exc:
        error = AppleUI.create_error_message("network_error", str(exc))
        text = f"{error['title']}\n\n{error['message']}"
        await client.send_message(message.chat.id, text)
        return
    
    # 显示处理状态
    status_text = AppleUI.format_message(
        title="正在克隆",
        icon=AppleUI.ICONS["copy"],
        content=f"正在克隆文件...\n\n`{link}`\n\n请稍候，这可能需要一些时间。"
    )
    
    status = await client.send_message(
        message.chat.id,
        status_text,
        reply_to_message_id=message.id
    )
    
    # 执行克隆
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, drive.clone, link)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="克隆成功",
            message=f"{result}\n\n文件已成功克隆到您的 Google Drive。",
            action="完成"
        )
        
        text = f"{success['title']}\n\n{success['message']}"
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "查看 Drive",
                callback_data="list_drive",
                icon=AppleUI.ICONS["gdrive"]
            )],
            [AppleUI.create_button(
                "返回主页",
                callback_data="back_home",
                icon=AppleUI.ICONS["home"]
            )]
        ])
        
        await client.edit_message_text(
            message.chat.id,
            status.id,
            text,
            reply_markup=keyboard
        )
        
    except Exception as exc:
        error = AppleUI.create_error_message(
            "not_found",
            custom_message=str(exc)
        )
        error_text = f"{error['title']}\n\n{error['message']}"
        await client.edit_message_text(
            message.chat.id,
            status.id,
            error_text
        )
    
    return


async def delete_handler(client, message):
    """
    Apple 风格的文件删除命令
    """
    user = message.from_user
    
    # 权限检查
    if user is None or user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = f"{error['title']}\n\n{error['message']}"
        await message.reply_text(text, quote=True)
        return
    
    # 授权检查
    if not is_authorized(str(user.id)):
        text = AppleUI.format_message(
            title="未授权",
            icon=AppleUI.ICONS["warning"],
            content=(
                "您需要先授权 Google Drive 才能使用此功能。\n\n"
                "请使用 `/auth` 命令完成授权。"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "立即授权",
                callback_data="auth_now",
                icon=AppleUI.ICONS["auth"]
            )]
        ])
        
        await message.reply_text(text, quote=True, reply_markup=keyboard)
        return
    
    user_id = user.id
    
    # 检查参数
    if not (len(message.command) > 1 or message.reply_to_message):
        text = AppleUI.format_message(
            title="缺少参数",
            icon=AppleUI.ICONS["warning"],
            content=(
                "请提供要删除的 Google Drive 链接。\n\n"
                f"__使用方法__\n"
                f"`/{BotCommands.Delete[0]} <Drive 链接>`\n\n"
                "__示例__\n"
                f"`/{BotCommands.Delete[0]} https://drive.google.com/file/d/xxxxx`"
            )
        )
        await message.reply_text(text, quote=True)
        return
    
    # 显示检查中状态
    sent_message = await message.reply_text(
        AppleUI.format_message(
            title="检查中",
            icon=AppleUI.ICONS["processing"],
            content="正在验证链接..."
        ),
        quote=True
    )
    
    # 获取链接
    if len(message.command) > 1:
        link = message.command[1]
    elif message.reply_to_message.entities and len(message.reply_to_message.entities) > 1 and message.reply_to_message.entities[1].url:
        link = message.reply_to_message.entities[1].url
    else:
        error = AppleUI.create_error_message("invalid_input")
        error_text = f"{error['title']}\n\n{error['message']}"
        await sent_message.edit(error_text)
        return
    
    LOGGER.info("Delete:%s: %s", user_id, link)
    
    # 获取 Drive 实例
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await sent_message.edit(drive_error_message(exc.code))
        return
    except Exception as exc:
        error = AppleUI.create_error_message("network_error", str(exc))
        error_text = f"{error['title']}\n\n{error['message']}"
        await sent_message.edit(error_text)
        return
    
    # 显示确认消息
    confirm_text = AppleUI.format_message(
        title="确认删除",
        icon=AppleUI.ICONS["warning"],
        content=(
            f"您确定要删除此文件吗？\n\n"
            f"`{link}`\n\n"
            "⚠️ __注意__：删除的文件将被移至回收站，"
            "可以在 30 天内恢复。"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "确认删除",
                callback_data=f"confirm_delete_{user_id}_{link}",
                icon=AppleUI.ICONS["delete"]
            ),
            AppleUI.create_button(
                "取消",
                callback_data="cancel_delete",
                icon=AppleUI.ICONS["cancel"]
            )
        ]
    ])
    
    # 由于 callback_data 长度限制，直接执行删除
    # 更新为删除中状态
    await sent_message.edit(
        AppleUI.format_message(
            title="删除中",
            icon=AppleUI.ICONS["delete"],
            content=f"正在删除文件...\n\n`{link}`"
        )
    )
    
    # 执行删除
    result = await asyncio.to_thread(drive.delete_file, link)
    
    # 成功消息
    success = AppleUI.create_success_message(
        title="删除成功",
        message=f"{result}\n\n文件已移至回收站。",
        action="完成"
    )
    
    text = f"{success['title']}\n\n{success['message']}"
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "清空回收站",
            callback_data="empty_trash",
            icon=AppleUI.ICONS["delete"]
        )],
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await sent_message.edit(text, reply_markup=keyboard)


async def emptytrash_handler(client, message):
    """
    Apple 风格的清空回收站命令
    """
    user = message.from_user
    
    # 权限检查
    if user is None or user.id not in SUDO_USERS:
        error = AppleUI.create_error_message("permission_denied")
        text = f"{error['title']}\n\n{error['message']}"
        await message.reply_text(text, quote=True)
        return
    
    # 授权检查
    if not is_authorized(str(user.id)):
        text = AppleUI.format_message(
            title="未授权",
            icon=AppleUI.ICONS["warning"],
            content=(
                "您需要先授权 Google Drive 才能使用此功能。\n\n"
                "请使用 `/auth` 命令完成授权。"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "立即授权",
                callback_data="auth_now",
                icon=AppleUI.ICONS["auth"]
            )]
        ])
        
        await message.reply_text(text, quote=True, reply_markup=keyboard)
        return
    
    user_id = user.id
    LOGGER.info("EmptyTrash: %s", user_id)
    
    # 显示确认消息
    confirm_text = AppleUI.format_message(
        title="确认清空回收站",
        icon=AppleUI.ICONS["warning"],
        content=(
            "您确定要清空 Google Drive 回收站吗？\n\n"
            "⚠️ __警告__：此操作不可逆！\n\n"
            "回收站中的所有文件将被永久删除，无法恢复。"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "确认清空",
                callback_data="confirm_empty_trash",
                icon=AppleUI.ICONS["error"]
            ),
            AppleUI.create_button(
                "取消",
                callback_data="cancel_empty_trash",
                icon=AppleUI.ICONS["cancel"]
            )
        ]
    ])
    
    await message.reply_text(
        confirm_text,
        quote=True,
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex(r"^confirm_empty_trash$"))
async def confirm_empty_trash_callback(client, callback_query: CallbackQuery):
    """
    确认清空回收站
    """
    user_id = callback_query.from_user.id
    
    # 更新为处理中状态
    await callback_query.message.edit_text(
        AppleUI.format_message(
            title="处理中",
            icon=AppleUI.ICONS["processing"],
            content="正在清空回收站..."
        )
    )
    
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await callback_query.message.edit_text(drive_error_message(exc.code))
        return
    except Exception as exc:
        error = AppleUI.create_error_message("network_error", str(exc))
        error_text = f"{error['title']}\n\n{error['message']}"
        await callback_query.message.edit_text(error_text)
        return
    
    # 执行清空
    msg = await asyncio.to_thread(drive.emptyTrash)
    
    # 成功消息
    success = AppleUI.create_success_message(
        title="清空成功",
        message=f"{msg}\n\n回收站已清空。",
        action="完成"
    )
    
    text = f"{success['title']}\n\n{success['message']}"
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("✅ 清空成功")


@Client.on_callback_query(filters.regex(r"^cancel_empty_trash$"))
async def cancel_empty_trash_callback(client, callback_query: CallbackQuery):
    """
    取消清空回收站
    """
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["info"],
        content="清空回收站操作已取消。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("已取消")


@Client.on_callback_query(filters.regex(r"^cancel_delete$"))
async def cancel_delete_callback(client, callback_query: CallbackQuery):
    """
    取消删除文件
    """
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["info"],
        content="删除操作已取消。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("已取消")
