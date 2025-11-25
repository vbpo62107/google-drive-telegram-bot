import urllib.parse as urlparse
from dataclasses import dataclass
from typing import Dict, Optional

from google_auth_oauthlib.flow import Flow
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import (
    G_DRIVE_CLIENT_ID,
    G_DRIVE_CLIENT_SECRET,
    LOGGER,
    OAUTH_SCOPE,
)
from bot.config import BotCommands, Messages
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
from bot.helpers.utils import CustomFilters
from bot.plugins.utils import mark_command_handled
from bot.modules.drive_helper import invalidate_drive_instance


LOOPBACK_REDIRECT_URI = "http://127.0.0.1:53682/oauth2callback"


@dataclass
class PendingFlow:
    flow: Flow
    device: str
    state: Optional[str]


def _build_flow() -> Flow:
    config = {
        "installed": {
            "client_id": G_DRIVE_CLIENT_ID,
            "client_secret": G_DRIVE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(config, scopes=[OAUTH_SCOPE])
    flow.redirect_uri = LOOPBACK_REDIRECT_URI
    return flow


def _sanitize_device_label(user_id: int, label: Optional[str]) -> str:
    base = label.strip() if label else f"telegram:{user_id}"
    cleaned = " ".join(base.split())
    return cleaned[:64] if cleaned else f"telegram:{user_id}"


def _parse_code(text: str) -> tuple[Optional[str], Optional[str]]:
    stripped = text.strip()
    if not stripped:
        return None, None
    # Ignore bot commands to avoid treating /ytdl 等命令为 OAuth 代码
    if stripped.startswith("/"):
        return None, None
    if "code=" in stripped:
        parsed = urlparse.urlparse(stripped)
        query = urlparse.parse_qs(parsed.query)
        code = query.get("code", [None])[-1]
        state = query.get("state", [None])[-1]
        return code, state
    return stripped or None, None


pending_flows: Dict[int, PendingFlow] = {}


@Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.Authorize))
async def _auth(client, message):
    mark_command_handled(message)
    user_id = message.from_user.id
    text = message.text or ""
    parts = text.split(maxsplit=1)
    device_label = _sanitize_device_label(user_id, parts[1] if len(parts) > 1 else None)
    record = gDriveDB.search(user_id)
    if record and record.is_oauth():
        try:
            credential_manager.build_credentials(user_id, record)
            gDriveDB.reset_failures(user_id)
            invalidate_drive_instance(user_id)
            await message.reply_text(Messages.ALREADY_AUTH, quote=True, parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as exc:
            LOGGER.warning("Failed to refresh existing credentials for %s: %s", user_id, exc)
    try:
        flow = _build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        pending_flows[user_id] = PendingFlow(flow=flow, device=device_label, state=state)
        LOGGER.info("AuthURL:%s", user_id)
        try:
            await message.reply_text(
                text=Messages.AUTH_TEXT.format(auth_url),
                quote=True,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Authorization URL", url=auth_url)]]),
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as exc:
            LOGGER.exception("send auth link failed: %s", exc)
            await message.reply_text(auth_url, quote=True, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        try:
            await message.reply_text(f"**ERROR:** ```{exc}```", quote=True, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(str(exc), quote=True, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(filters.private & filters.incoming & filters.command(BotCommands.Revoke) & CustomFilters.auth_users)
async def _revoke(client, message):
    mark_command_handled(message)
    user_id = message.from_user.id
    try:
        gDriveDB._clear(user_id)
        pending_flows.pop(user_id, None)
        invalidate_drive_instance(user_id)
        LOGGER.info("Revoked:%s", user_id)
        await message.reply_text(Messages.REVOKED, quote=True, parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        await message.reply_text(f"**ERROR:** ```{exc}```", quote=True, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(filters.private & filters.incoming & filters.text)
async def _token(client, message):
    user_id = message.from_user.id
    entry = pending_flows.get(user_id)
    if not entry:
        return
    code, state = _parse_code(message.text or "")
    if not code:
        return
    if entry.state and state and state != entry.state:
        return
    sent_message = await message.reply_text(
        "Checking received code...",
        quote=True,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    try:
        entry.flow.fetch_token(code=code)
        credentials = entry.flow.credentials
        payload, fingerprint = credential_manager.serialize_oauth(credentials)
        gDriveDB.save_credentials(
            user_id,
            mode="oauth",
            payload=payload,
            fingerprint=fingerprint,
            device=entry.device,
        )
        gDriveDB.reset_failures(user_id)
        invalidate_drive_instance(user_id)
        await sent_message.edit(Messages.AUTH_SUCCESSFULLY)
    except Exception as exc:
        LOGGER.error("Auth failed for %s: %s", user_id, exc)
        await sent_message.edit(Messages.INVALID_AUTH_CODE)
    finally:
        pending_flows.pop(user_id, None)
