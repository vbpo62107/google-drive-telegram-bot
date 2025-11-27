import asyncio
from pyrogram import Client, filters

from bot import LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper import gDriveDB, idsDB
from bot.helpers.utils import format_bytes
from bot.modules.drive_helper import DriveAccessError, drive_error_message, get_drive_instance

FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_MESSAGE_LENGTH = 4000


def _normalize_size(value):
    if value is None:
        return ""
    try:
        return format_bytes(int(value))
    except (TypeError, ValueError):
        return ""


def _sort_key(item):
    mime_type = item.get("mimeType")
    name = item.get("name") or ""
    return (0 if mime_type == FOLDER_MIME else 1, name.lower())


async def _fetch_children(drive, folder_id):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, drive.getFilesByFolderId, folder_id)


async def _resolve_path(drive, default_parent, raw):
    alias = raw.strip()
    if not alias:
        return default_parent, Messages.LIST_DEFAULT_LABEL
    if alias in {".", "./"}:
        return default_parent, Messages.LIST_DEFAULT_LABEL
    if alias.lower() in {"root", "/"}:
        return "root", "root"
    if alias.lower() in {"default", "home"}:
        return default_parent, Messages.LIST_DEFAULT_LABEL
    if "/" in alias:
        is_absolute = alias.startswith("/")
        segments = [segment for segment in alias.strip("/").split("/") if segment]
        current_id = "root" if is_absolute else default_parent
        path_label = "/".join(segments) if segments else Messages.LIST_DEFAULT_LABEL
        for segment in segments:
            children = await _fetch_children(drive, current_id)
            match = None
            for item in children:
                if item.get("mimeType") == FOLDER_MIME and item.get("name", "").lower() == segment.lower():
                    match = item.get("id")
                    break
            if not match:
                raise ValueError(Messages.LIST_PATH_NOT_FOUND.format(segment))
            current_id = match
        return current_id, path_label
    children = await _fetch_children(drive, default_parent)
    for item in children:
        if item.get("mimeType") == FOLDER_MIME and item.get("name", "").lower() == alias.lower():
            return item.get("id"), alias
    return alias, alias


def _build_entries(files):
    entries = []
    for index, item in enumerate(sorted(files, key=_sort_key), start=1):
        name = item.get("name") or ""
        file_id = item.get("id") or ""
        mime_type = item.get("mimeType")
        if mime_type == FOLDER_MIME:
            entries.append(f"{index}. 📁 `{name}`\n   ID: `{file_id}`")
        else:
            size = _normalize_size(item.get("size"))
            if size:
                entries.append(f"{index}. 📄 `{name}`\n   ID: `{file_id}`\n   大小: {size}")
            else:
                entries.append(f"{index}. 📄 `{name}`\n   ID: `{file_id}`")
    return entries


def _split_entry(entry, limit):
    if limit <= 0:
        return [entry]
    return [entry[i:i + limit] for i in range(0, len(entry), limit)]


def _chunk_messages(header, cont_header, entries):
    if not entries:
        return [header]
    max_header_length = max(len(header), len(cont_header))
    usable_limit = MAX_MESSAGE_LENGTH - max_header_length - 1
    if usable_limit <= 0:
        usable_limit = MAX_MESSAGE_LENGTH // 2 or MAX_MESSAGE_LENGTH
    chunks = []
    current_header = header
    current_entries = []
    current_length = len(current_header)
    for entry in entries:
        parts = [entry]
        if len(entry) + 1 + max_header_length > MAX_MESSAGE_LENGTH:
            parts = _split_entry(entry, usable_limit)
        for part in parts:
            while True:
                if current_entries:
                    proposed_length = current_length + 1 + len(part)
                else:
                    proposed_length = len(current_header) + 1 + len(part)
                if proposed_length <= MAX_MESSAGE_LENGTH:
                    current_entries.append(part)
                    current_length = proposed_length
                    break
                chunk_text = current_header
                if current_entries:
                    chunk_text += "\n" + "\n".join(current_entries)
                chunks.append(chunk_text)
                current_header = cont_header
                current_entries = []
                current_length = len(current_header)
    if current_entries:
        chunk_text = current_header + "\n" + "\n".join(current_entries)
        chunks.append(chunk_text)
    return [chunk for chunk in chunks if chunk.strip()]


# @Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.ListDrive))  # 由 __main__.py 注册
async def list_drive_handler(client, message):
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, "❌ 您没有权限使用此命令.")
        return
    user_id = message.from_user.id
    try:
        if not gDriveDB.is_authorized(user_id):
            await client.send_message(message.chat.id, Messages.NOT_AUTH)
            return
    except Exception as exc:
        LOGGER.error("ListDrive auth check failed for user %s: %s", user_id, exc)
        await client.send_message(message.chat.id, Messages.DB_ERROR, quote=True)
        return
    parts = (message.text or "").split(maxsplit=1)
    target = parts[1] if len(parts) > 1 else ""
    try:
        drive = await get_drive_instance(user_id)
    except DriveAccessError as exc:
        await client.send_message(message.chat.id, drive_error_message(exc.code))
        return
    except Exception as exc:
        await client.send_message(message.chat.id, f"❌ {exc}")
        return
    default_parent = idsDB.search_parent(user_id)
    try:
        folder_id, label = await _resolve_path(drive, default_parent, target or "")
        files = await _fetch_children(drive, folder_id)
    except Exception as exc:
        await client.send_message(message.chat.id, Messages.LIST_ERROR.format(exc))
        return
    if not files:
        await client.send_message(message.chat.id, Messages.LIST_EMPTY.format(label))
        return
    entries = _build_entries(files)
    header = Messages.LIST_HEADER.format(label, folder_id)
    cont_header = Messages.LIST_CONT_HEADER.format(label, folder_id)
    chunks = _chunk_messages(header, cont_header, entries)
    for chunk in chunks:
        await client.send_message(message.chat.id, chunk)
