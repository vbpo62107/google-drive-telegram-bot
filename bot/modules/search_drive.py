import asyncio

from pyrogram import Client, filters

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import format_bytes
from bot.modules.drive_helper import DriveAccessError, drive_error_message, get_drive_instance

FOLDER_MIME = "application/vnd.google-apps.folder"


def _format_size(value):
    if value is None:
        return ""
    try:
        return format_bytes(int(value))
    except (TypeError, ValueError):
        return ""


# @Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.SearchDrive))  # 由 __main__.py 注册
async def search_drive_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "⚠️ 您没有权限使用此命令.")
        return
    user_id = message.from_user.id
    try:
        if not gDriveDB.is_authorized(user_id):
            await client.send_message(message.chat.id, Messages.NOT_AUTH)
            return
    except Exception as exc:
        LOGGER.error("SearchDrive auth check failed for user %s: %s", user_id, exc)
        await client.send_message(message.chat.id, Messages.DB_ERROR)
        return
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await client.send_message(
            message.chat.id,
            Messages.SEARCH_USAGE.format(BotCommands.SearchDrive[0], BotCommands.SearchDrive[0]),
        )
        return
    query_text = parts[1].strip()
    page_token = None
    if "|" in query_text:
        segment, token = query_text.split("|", 1)
        query_text = segment.strip()
        token = token.strip()
        page_token = token or None
    if not query_text:
        await client.send_message(
            message.chat.id,
            Messages.SEARCH_USAGE.format(BotCommands.SearchDrive[0], BotCommands.SearchDrive[0]),
        )
        return
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await client.send_message(message.chat.id, drive_error_message(exc.code))
        return
    except Exception as exc:
        await client.send_message(message.chat.id, f"⚠️ {exc}")
        return
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, drive.search_files, query_text, page_token)
    except Exception as exc:
        await client.send_message(message.chat.id, Messages.SEARCH_ERROR.format(exc))
        return
    if not isinstance(response, dict):
        await client.send_message(message.chat.id, Messages.SEARCH_ERROR.format("Unexpected response"))
        return
    files = response.get("files", [])
    next_token = response.get("nextPageToken")
    if not files:
        await client.send_message(message.chat.id, Messages.SEARCH_NO_RESULTS.format(query_text))
        return
    lines = [Messages.SEARCH_RESULTS_HEADER.format(query_text)]
    for index, item in enumerate(files, start=1):
        name = item.get("name") or ""
        file_id = item.get("id") or ""
        mime_type = item.get("mimeType") or ""
        size_text = _format_size(item.get("size"))
        if mime_type == FOLDER_MIME:
            type_label = "文件夹"
            link = f"https://drive.google.com/drive/folders/{file_id}"
        else:
            type_label = "文件"
            link = f"https://drive.google.com/uc?id={file_id}&export=download"
        entry = f"{index}. `{name}`\n   类型: {type_label}"
        if size_text:
            entry += f"\n   大小: {size_text}"
        entry += f"\n   链接: {link}"
        lines.append(entry)
    if next_token:
        lines.append(Messages.SEARCH_PAGE_TOKEN.format(next_token))
    message_text = "\n".join(lines)
    if len(message_text) <= 4000:
        await client.send_message(message.chat.id, message_text)
        return
    chunks = []
    current = []
    current_length = 0
    for line in lines:
        if current_length + len(line) + (1 if current else 0) > 4000:
            chunks.append("\n".join(current))
            current = [line]
            current_length = len(line)
        else:
            if current:
                current_length += 1 + len(line)
                current.append(line)
            else:
                current.append(line)
                current_length = len(line)
    if current:
        chunks.append("\n".join(current))
    for chunk in chunks:
        await client.send_message(message.chat.id, chunk)
