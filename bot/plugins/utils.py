"""
System Utility Commands - Apple Design Edition
系统工具命令 - Apple 设计版

提供系统管理相关的命令，包括日志查看和重启。
仅管理员可用。
"""
import asyncio
import shutil
from os import execl
from sys import executable
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError

from bot import DOWNLOAD_DIRECTORY, LOGGER, SUDO_USERS
from bot.helpers.utils import get_floodwait_seconds
from bot.ui.apple_ui import AppleUI


@Client.on_message(
    filters.private & filters.incoming & filters.command(["log"]) & filters.user(SUDO_USERS),
    group=2,
)
async def _send_log(client: Client, message: Message) -> None:
    """
    处理 /log 命令，发送系统日志文件
    
    仅管理员可用。用于排查问题和监控系统状态。
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    # 显示准备状态
    status = await AppleUI.send_processing(
        client,
        message.chat.id,
        "📄 准备日志",
        "正在读取系统日志文件...",
        "请稍候，这可能需要几秒钟。",
    )
    
    try:
        # 读取日志文件
        with open("log.txt", "rb") as handle:
            try:
                # 更新为发送状态
                await client.edit_message_text(
                    message.chat.id,
                    status.id,
                    AppleUI.format_message(
                        "📤 发送中",
                        "正在上传日志文件...",
                        "请保持连接。",
                    ),
                )
                
                # 发送文件
                await client.send_document(
                    message.chat.id,
                    document=handle,
                    file_name=handle.name,
                    reply_to_message_id=message.id,
                    parse_mode=ParseMode.MARKDOWN,
                )
                
                # 删除状态消息
                await status.delete()
                
                # 发送成功通知
                await AppleUI.send_success(
                    client,
                    message.chat.id,
                    "✅ 日志发送成功",
                    "系统日志文件已上传。",
                    f"📄 **文件名：** `{handle.name}`\n\n"
                    f"⚠️ 请注意保护日志文件的隐私，不要分享给他人。",
                )
                
                LOGGER.info("Log file sent to %s", message.from_user.id)
                
            except FloodWait as exc:
                wait_seconds = get_floodwait_seconds(exc) or 1
                
                await client.edit_message_text(
                    message.chat.id,
                    status.id,
                    AppleUI.format_message(
                        "⏳ 请稍候",
                        f"发送过于频繁，需要等待 {wait_seconds} 秒。",
                        "正在重试...",
                    ),
                )
                
                await asyncio.sleep(wait_seconds)
                # 重试发送
                await _send_log(client, message)
                
            except RPCError as exc:
                await client.edit_message_text(
                    message.chat.id,
                    status.id,
                    AppleUI.format_message(
                        "❌ 发送失败",
                        "发送日志文件时发生错误。",
                        f"**错误详情：** {str(exc)}",
                    ),
                )
                
    except FileNotFoundError:
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "❌ 文件不存在",
                "未找到日志文件。",
                "可能系统还没有生成日志，或日志文件已被删除。",
            ),
        )
    except Exception as exc:
        await client.edit_message_text(
            message.chat.id,
            status.id,
            AppleUI.format_message(
                "❌ 读取失败",
                "读取日志文件时发生错误。",
                f"**错误详情：** {str(exc)}",
            ),
        )


@Client.on_message(
    filters.private & filters.incoming & filters.command(["restart"]) & filters.user(SUDO_USERS),
    group=2,
)
async def _restart(client: Client, message: Message) -> None:
    """
    处理 /restart 命令，重启 Bot
    
    仅管理员可用。会清空下载目录并重启系统。
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    # 显示确认消息
    confirmation = await AppleUI.send_info(
        client,
        message.chat.id,
        "⚠️ 确认重启",
        "您确定要重启 Bot 吗？",
        "**此操作将：**\n"
        "• 清空所有下载中的文件\n"
        "• 中断正在进行的任务\n"
        "• 重启需要几秒钟\n\n"
        "⚠️ **注意：**此操作不可恢复！\n\n"
        "请再次发送 `/restart confirm` 确认重启。",
    )
    
    # 检查是否有确认参数
    if len(message.command) > 1 and message.command[1].lower() == "confirm":
        # 显示重启状态
        status = await client.edit_message_text(
            message.chat.id,
            confirmation.id,
            AppleUI.format_message(
                "♻️ 正在重启",
                "Bot 正在重启，请稍候...",
                "**步骤：**\n"
                "1️⃣ 清空下载目录...\n"
                "2️⃣ 关闭当前进程...\n"
                "3️⃣ 启动新进程...",
            ),
        )
        
        try:
            # 清空下载目录
            shutil.rmtree(DOWNLOAD_DIRECTORY, ignore_errors=True)
            LOGGER.info("Deleted DOWNLOAD_DIRECTORY successfully.")
            
            # 更新状态
            await client.edit_message_text(
                message.chat.id,
                status.id,
                AppleUI.format_message(
                    "✅ 重启成功",
                    "Bot 正在重启...",
                    "🔄 请稍候 10-30 秒，然后再次使用 Bot。\n\n"
                    "ℹ️ 如果超过 1 分钟未响应，请检查服务器状态。",
                ),
            )
            
            LOGGER.info("%s: Restarting...", message.from_user.id)
            
            # 重启
            execl(executable, executable, "-m", "bot")
            
        except Exception as exc:
            await client.edit_message_text(
                message.chat.id,
                status.id,
                AppleUI.format_message(
                    "❌ 重启失败",
                    "重启 Bot 时发生错误。",
                    f"**错误详情：** {str(exc)}\n\n"
                    f"请手动重启服务器或联系管理员。",
                ),
            )
            LOGGER.error("Restart failed: %s", exc)


log_handler = _send_log
restart_handler = _restart
