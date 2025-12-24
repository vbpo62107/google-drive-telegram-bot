"""
Command Logger Plugin - Apple Design Edition
命令日志插件 - Apple 设计版

记录所有用户命令和消息，用于监控、调试和分析。
这是一个后台插件，不直接与用户交互。
"""
from itertools import chain
from typing import List, Optional

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.types import Message

from bot import LOGGER
from bot.config import BotCommands

# 初始化日志
_log_separator = "-" * 40
LOGGER.info(_log_separator)
LOGGER.info("Loading command_logger plugin")
LOGGER.info("YtDl commands: %s", BotCommands.YtDl)
LOGGER.info("Download commands: %s", BotCommands.Download)

# 构建命令别名列表
COMMAND_ALIASES: List[str] = list(
    chain(
        BotCommands.Clone,
        BotCommands.Delete,
        BotCommands.EmptyTrash,
        BotCommands.Download,
        BotCommands.YtDl,
        BotCommands.ListDrive,
        BotCommands.SearchDrive,
        BotCommands.SetFolder,
        BotCommands.Authorize,
        BotCommands.AuthMode,
        BotCommands.Revoke,
    )
)

LOGGER.info("Command aliases registered: %s", COMMAND_ALIASES)
LOGGER.info("Total command aliases: %d", len(COMMAND_ALIASES))
LOGGER.info("'ytdl' in aliases: %s", "ytdl" in COMMAND_ALIASES)
LOGGER.info(_log_separator)


def _normalize_command(message: Message) -> Optional[str]:
    """
    从消息中提取和规范化命令
    
    处理各种命令格式：
    - /command
    - /command@botname
    - /command args
    
    Args:
        message: Pyrogram 消息对象
        
    Returns:
        规范化的命令名（小写，不带 /），如果不是命令则返回 None
        
    Examples:
        >>> _normalize_command(message_with_text="/start")
        'start'
        >>> _normalize_command(message_with_text="/help@mybot")
        'help'
        >>> _normalize_command(message_with_text="Hello")
        None
    """
    # 尝试从 message.command 属性获取
    if hasattr(message, "command") and message.command:
        command = message.command[0] or ""
        return command.lstrip("/").lower()
    
    # 备用方案：从文本解析
    text = (message.text or "").strip()
    
    if not text.startswith("/"):
        return None
    
    # 提取命令部分（去除 bot 名称和参数）
    command_part = text.split()[0] if " " in text else text
    command = command_part.split("@")[0].lstrip("/").lower()
    
    return command if command else None


@Client.on_message(filters.incoming & filters.command(COMMAND_ALIASES), group=0)
async def _command_logger(client: Client, message: Message) -> None:
    """
    记录所有已注册的命令
    
    此处理器在 group=0 执行，优先级最高，确保所有命令都被记录。
    使用 ContinuePropagation 允许后续处理器继续处理此消息。
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
        
    Raises:
        ContinuePropagation: 总是抛出，以便命令继续被处理
    """
    command = _normalize_command(message)
    
    # 记录详细信息
    user_id = getattr(message.from_user, "id", "Unknown")
    chat_id = getattr(message.chat, "id", "Unknown")
    chat_type = getattr(message.chat, "type", "Unknown")
    message_text = (message.text or "")[:100]  # 限制长度避免日志过长
    
    LOGGER.info(
        "[COMMAND] User=%s Chat=%s Type=%s Cmd=/%s Text=%r",
        user_id,
        chat_id,
        chat_type,
        command,
        message_text,
    )
    
    # 允许命令继续传播到其他处理器
    raise ContinuePropagation


@Client.on_message(filters.incoming, group=1)
async def _message_logger(client: Client, message: Message) -> None:
    """
    记录所有入站消息
    
    此处理器在 group=1 执行，优先级较低，用于记录非命令消息。
    不会阻止消息传播。
    
    Args:
        client: Pyrogram 客户端实例
        message: 用户消息对象
    """
    command = _normalize_command(message)
    
    # 记录消息信息
    user_id = getattr(message.from_user, "id", "Unknown")
    chat_id = getattr(message.chat, "id", "Unknown")
    chat_type = getattr(message.chat, "type", "Unknown")
    message_text = (message.text or message.caption or "")[:100]  # 支持媒体消息
    
    # 记录级别：命令用 INFO，普通消息用 DEBUG
    if command:
        LOGGER.debug(
            "[MESSAGE] User=%s Chat=%s Type=%s Cmd=/%s Text=%r",
            user_id,
            chat_id,
            chat_type,
            command,
            message_text,
        )
    else:
        LOGGER.debug(
            "[MESSAGE] User=%s Chat=%s Type=%s Text=%r",
            user_id,
            chat_id,
            chat_type,
            message_text,
        )


# 导出处理器（可选）
command_logger_handler = _command_logger
message_logger_handler = _message_logger

# 插件加载完成
LOGGER.info("command_logger plugin loaded successfully")
