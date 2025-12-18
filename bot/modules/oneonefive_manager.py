from __future__ import annotations

import asyncio
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Optional

from pyrogram import Client, filters

from bot import DOWNLOAD_DIRECTORY, LOGGER, SUDO_USERS
from bot.config import BotCommands, Messages
from bot.helpers.sql_helper import get_session
from bot.helpers.sql_helper.mirror_tasks import MirrorTask
from bot.helpers.sql_helper.oneonefive_db import get_oneonefive_auth, save_oneonefive_auth
from bot.helpers.utils import CustomFilters
from bot.utils.messages_utils import render_permission_error

_115_utils = import_module("bot.helpers.115_utils")
OneOneFiveAuthError = _115_utils.OneOneFiveAuthError
OneOneFiveUploadError = _115_utils.OneOneFiveUploadError
upload_to_115_for_user = _115_utils.upload_to_115_for_user


DOWNLOAD_PATH = Path(DOWNLOAD_DIRECTORY)


def _format_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "未知"
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def _detect_auth_method(auth: Optional[dict]) -> str:
    if not auth:
        return "未设置"
    if auth.get("cookies"):
        return "Cookies"
    if auth.get("token"):
        return "Token"
    return "未知"


def _parse_payload(message) -> tuple[Optional[str], Optional[str]]:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) <= 1:
        return None, None
    payload = parts[1].strip()
    if not payload:
        return None, None
    if "|" in payload:
        left, right = payload.split("|", 1)
        return left.strip() or None, right.strip() or None
    tokens = payload.split()
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0], None
    return tokens[0], " ".join(tokens[1:])


def _normalize_pid(pid_text: Optional[str]) -> int | str:
    if not pid_text:
        return 0
    pid_text = pid_text.strip()
    if pid_text.isdigit():
        try:
            return int(pid_text)
        except ValueError:
            return pid_text
    return pid_text


def _find_task_file(user_id: int) -> Optional[Path]:
    with get_session() as session:
        record = (
            session.query(MirrorTask)
            .filter(MirrorTask.user_id == user_id)
            .order_by(MirrorTask.updated_at.desc())
            .first()
        )
    if not record:
        return None
    base_dir = DOWNLOAD_PATH / f"task_{record.id}"
    candidates = [base_dir / record.file_name, base_dir / f"{record.file_name}.part"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _find_by_name(name: str) -> Optional[Path]:
    direct = Path(name)
    if direct.is_file():
        return direct
    nested = DOWNLOAD_PATH / name
    if nested.is_file():
        return nested
    if not DOWNLOAD_PATH.exists():
        return None
    for path in DOWNLOAD_PATH.rglob("*"):
        if path.is_file() and path.name == name:
            return path
    return None


def _latest_download_file() -> Optional[Path]:
    if not DOWNLOAD_PATH.exists():
        return None
    newest: Optional[Path] = None
    for path in DOWNLOAD_PATH.rglob("*"):
        if not path.is_file():
            continue
        if newest is None:
            newest = path
            continue
        try:
            if path.stat().st_mtime > newest.stat().st_mtime:
                newest = path
        except FileNotFoundError:
            continue
    return newest


def _resolve_file_path(user_id: int, hint: Optional[str]) -> Optional[Path]:
    if hint:
        hinted = _find_by_name(hint)
        if hinted and hinted.is_file():
            return hinted
    task_file = _find_task_file(user_id)
    if task_file:
        return task_file
    return _latest_download_file()


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(BotCommands.OneOneFiveAuth)
    & CustomFilters.auth_users,
)
async def oneonefive_auth_handler(client: Client, message) -> None:
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, render_permission_error("115 授权", "使用"), quote=True)
        return

    args = list(message.command or [])
    if len(args) <= 1:
        await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_USAGE, quote=True)
        return

    action = (args[1] or "").lower()
    user_id = message.from_user.id

    if action == "info":
        auth = get_oneonefive_auth(user_id)
        if not auth:
            await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_REQUIRED, quote=True)
            return
        method = _detect_auth_method(auth)
        updated = _format_datetime(auth.get("updated_at"))
        await client.send_message(
            message.chat.id,
            Messages.ONEONEFIVE_AUTH_INFO.format(method=method, updated_at=updated),
            quote=True,
        )
        return

    if action == "cookies":
        if len(args) <= 2:
            await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_USAGE, quote=True)
            return
        cookies = " ".join(args[2:]).strip()
        try:
            record = save_oneonefive_auth(user_id, cookies=cookies)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to save 115 cookies auth: %s", exc)
            await client.send_message(
                message.chat.id,
                Messages.ONEONEFIVE_AUTH_FAILED.format(reason=str(exc)),
                quote=True,
            )
            return
        updated = _format_datetime(record.get("updated_at"))
        await client.send_message(
            message.chat.id,
            Messages.ONEONEFIVE_AUTH_SAVED.format(method="Cookies", updated_at=updated),
            quote=True,
        )
        return

    if action == "token":
        if len(args) <= 2:
            await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_USAGE, quote=True)
            return
        token = args[2].strip()
        app_id = args[3].strip() if len(args) > 3 else None
        try:
            record = save_oneonefive_auth(user_id, token=token, app_id=app_id)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to save 115 token auth: %s", exc)
            await client.send_message(
                message.chat.id,
                Messages.ONEONEFIVE_AUTH_FAILED.format(reason=str(exc)),
                quote=True,
            )
            return
        updated = _format_datetime(record.get("updated_at"))
        await client.send_message(
            message.chat.id,
            Messages.ONEONEFIVE_AUTH_SAVED.format(method="Token", updated_at=updated),
            quote=True,
        )
        return

    await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_USAGE, quote=True)


@Client.on_message(
    filters.private
    & filters.incoming
    & filters.command(BotCommands.OneOneFiveUpload)
    & CustomFilters.auth_users,
)
async def oneonefive_upload_handler(client: Client, message) -> None:
    if message.from_user is None or message.from_user.id not in SUDO_USERS:
        await client.send_message(message.chat.id, render_permission_error("115 上传", "使用"), quote=True)
        return

    user_id = message.from_user.id
    file_hint, pid_text = _parse_payload(message)
    pid = _normalize_pid(pid_text)

    file_path = _resolve_file_path(user_id, file_hint)
    if not file_path or not file_path.is_file():
        await client.send_message(message.chat.id, Messages.ONEONEFIVE_RECENT_FILE_MISSING, quote=True)
        return

    auth = get_oneonefive_auth(user_id)
    if not auth:
        await client.send_message(message.chat.id, Messages.ONEONEFIVE_AUTH_REQUIRED, quote=True)
        return

    status = await client.send_message(
        message.chat.id,
        Messages.ONEONEFIVE_UPLOAD_PREPARING.format(filename=file_path.name, pid=pid),
        reply_to_message_id=message.id,
    )

    loop = asyncio.get_running_loop()
    try:
        share_info = await loop.run_in_executor(
            None,
            lambda: upload_to_115_for_user(
                user_id=user_id,
                file_path=str(file_path),
                pid=pid,
                filename=file_path.name,
            ),
        )
    except OneOneFiveAuthError as exc:
        LOGGER.warning("115 auth error for user %s: %s", user_id, exc)
        await client.edit_message_text(message.chat.id, status.id, Messages.ONEONEFIVE_AUTH_REQUIRED)
        return
    except OneOneFiveUploadError as exc:
        LOGGER.error("115 upload failed for user %s: %s", user_id, exc)
        await client.edit_message_text(
            message.chat.id,
            status.id,
            Messages.ONEONEFIVE_UPLOAD_FAILED.format(reason=str(exc)),
        )
        return
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unexpected 115 upload error for user %s: %s", user_id, exc)
        await client.edit_message_text(
            message.chat.id,
            status.id,
            Messages.ONEONEFIVE_UPLOAD_FAILED.format(reason=str(exc)),
        )
        return

    codes = []
    if getattr(share_info, "share_code", None):
        codes.append(f"提取码：`{share_info.share_code}`")
    if getattr(share_info, "receive_code", None):
        codes.append(f"接收码：`{share_info.receive_code}`")
    extra_lines = "\n".join(codes) if codes else "无提取码/接收码"

    await client.edit_message_text(
        message.chat.id,
        status.id,
        Messages.ONEONEFIVE_UPLOAD_SUCCESS.format(
            filename=file_path.name,
            share_url=getattr(share_info, "share_url", ""),
            extra_lines=extra_lines,
        ),
    )
