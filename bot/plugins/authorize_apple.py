"""
Apple 风格的授权命令
重构 /auth 和 /revoke 命令以符合 Apple 设计语言
"""

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
from bot.modules.drive_helper import invalidate_drive_instance
from bot.ui_apple_style import AppleUI


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


async def _auth(client, message):
    """
    Apple 风格的 Google Drive 授权命令
    """
    user_id = message.from_user.id
    text = message.text or ""
    parts = text.split(maxsplit=1)
    device_label = _sanitize_device_label(user_id, parts[1] if len(parts) > 1 else None)
    
    # 检查是否已授权
    record = gDriveDB.search(user_id)
    if record and record.is_oauth():
        try:
            credential_manager.build_credentials(user_id, record)
            gDriveDB.reset_failures(user_id)
            invalidate_drive_instance(user_id)
            
            # Apple 风格的已授权消息
            text = AppleUI.format_message(
                title="已授权",
                icon=AppleUI.ICONS["success"],
                content=(
                    "您的 Google Drive 已经授权成功。\n\n"
                    f"💻 设备：`{device_label}`\n\n"
                    "如需重新授权，请先使用 `/revoke` 撤销当前授权。"
                )
            )
            
            keyboard = AppleUI.create_keyboard([
                [AppleUI.create_button(
                    "撤销授权",
                    callback_data="revoke_auth",
                    icon=AppleUI.ICONS["cancel"]
                )],
                [AppleUI.create_button(
                    "返回主页",
                    callback_data="back_home",
                    icon=AppleUI.ICONS["home"]
                )]
            ])
            
            await message.reply_text(
                text,
                quote=True,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        except Exception as exc:
            LOGGER.warning("Failed to refresh existing credentials for %s: %s", user_id, exc)
    
    # 开始授权流程
    try:
        flow = _build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        pending_flows[user_id] = PendingFlow(flow=flow, device=device_label, state=state)
        LOGGER.info("AuthURL:%s", user_id)
        
        # Apple 风格的授权消息
        text = AppleUI.format_message(
            title="Google Drive 授权",
            icon=AppleUI.ICONS["auth"],
            subtitle="请完成以下步骤",
            content=(
                "**步骤 1** - 点击下方按钮打开授权页面\n\n"
                "**步骤 2** - 登录您的 Google 账户\n\n"
                "**步骤 3** - 允许访问权限\n\n"
                "**步骤 4** - 复制授权代码并发送给我\n\n"
                "🔒 __您的数据安全是我们的首要任务__"
            ),
            footer="⚠️ 授权链接仅在 10 分钟内有效"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "打开授权页面",
                url=auth_url,
                icon="🔓"
            )],
            [AppleUI.create_button(
                "取消授权",
                callback_data="cancel_auth",
                icon=AppleUI.ICONS["cancel"]
            )]
        ])
        
        try:
            await message.reply_text(
                text=text,
                quote=True,
                reply_markup=keyboard,
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as exc:
            LOGGER.exception("send auth link failed: %s", exc)
            # 备用：直接发送链接
            fallback_text = AppleUI.format_message(
                title="授权链接",
                icon=AppleUI.ICONS["link"],
                content=f"{auth_url}\n\n请复制授权代码并发送给我"
            )
            await message.reply_text(
                fallback_text,
                quote=True,
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as exc:
        error = AppleUI.create_error_message(
            "auth_failed",
            custom_message=str(exc)
        )
        error_text = f"{error['title']}\n\n{error['message']}"
        await message.reply_text(
            error_text,
            quote=True,
            parse_mode=ParseMode.MARKDOWN
        )


async def _revoke(client, message):
    """
    Apple 风格的撤销授权命令
    """
    user_id = message.from_user.id
    
    # 显示确认消息
    text = AppleUI.format_message(
        title="撤销授权",
        icon=AppleUI.ICONS["warning"],
        content=(
            "您确定要撤销 Google Drive 授权吗？\n\n"
            "撤销后您将无法：\n"
            "• 上传文件到 Drive\n"
            "• 管理 Drive 文件\n"
            "• 使用镜像功能\n\n"
            "您可以随时使用 `/auth` 重新授权。"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button(
                "确认撤销",
                callback_data="confirm_revoke",
                icon=AppleUI.ICONS["error"]
            ),
            AppleUI.create_button(
                "取消",
                callback_data="cancel_revoke",
                icon=AppleUI.ICONS["cancel"]
            )
        ]
    ])
    
    await message.reply_text(
        text,
        quote=True,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@Client.on_callback_query(filters.regex(r"^confirm_revoke$"))
async def confirm_revoke_callback(client, callback_query):
    """
    确认撤销授权
    """
    user_id = callback_query.from_user.id
    
    try:
        gDriveDB._clear(user_id)
        pending_flows.pop(user_id, None)
        invalidate_drive_instance(user_id)
        LOGGER.info("Revoked:%s", user_id)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="撤销成功",
            message=(
                "您的 Google Drive 授权已被撤销。\n\n"
                "要重新使用 Drive 功能，请使用 `/auth` 命令重新授权。"
            ),
            action="已完成"
        )
        
        text = f"{success['title']}\n\n{success['message']}"
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "重新授权",
                callback_data="auth_now",
                icon=AppleUI.ICONS["auth"]
            )],
            [AppleUI.create_button(
                "返回主页",
                callback_data="back_home",
                icon=AppleUI.ICONS["home"]
            )]
        ])
        
        await callback_query.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer("✅ 撤销成功")
        
    except Exception as exc:
        error = AppleUI.create_error_message(
            "permission_denied",
            custom_message=str(exc)
        )
        error_text = f"{error['title']}\n\n{error['message']}"
        await callback_query.message.edit_text(
            error_text,
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer("❌ 撤销失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_revoke$"))
async def cancel_revoke_callback(client, callback_query):
    """
    取消撤销操作
    """
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["info"],
        content="撤销操作已取消，您的授权仍然有效。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer("已取消")


@Client.on_callback_query(filters.regex(r"^cancel_auth$"))
async def cancel_auth_callback(client, callback_query):
    """
    取消授权流程
    """
    user_id = callback_query.from_user.id
    pending_flows.pop(user_id, None)
    
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["info"],
        content="授权流程已取消。\n\n如需重新授权，请使用 `/auth` 命令。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button(
            "返回主页",
            callback_data="back_home",
            icon=AppleUI.ICONS["home"]
        )]
    ])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer("已取消")


@Client.on_message(filters.private & filters.incoming & filters.text, group=0)
async def _token(client, message):
    """
    处理授权代码
    """
    user_id = message.from_user.id
    entry = pending_flows.get(user_id)
    if not entry:
        return
    
    code, state = _parse_code(message.text or "")
    if not code:
        return
    
    if entry.state and state and state != entry.state:
        return
    
    # 显示处理中消息
    sent_message = await message.reply_text(
        AppleUI.format_message(
            title="验证中",
            icon=AppleUI.ICONS["processing"],
            content="正在验证您的授权代码..."
        ),
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
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="授权成功",
            message=(
                "您的 Google Drive 已成功授权！\n\n"
                f"💻 设备：`{entry.device}`\n\n"
                "现在您可以：\n"
                "• 上传文件到 Drive\n"
                "• 管理您的文件\n"
                "• 使用镜像功能\n\n"
                "🚀 快发送一个文件试试吧！"
            ),
            action="完成"
        )
        
        text = f"{success['title']}\n\n{success['message']}"
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "设置上传文件夹",
                callback_data="set_folder",
                icon=AppleUI.ICONS["folder"]
            )],
            [AppleUI.create_button(
                "查看帮助",
                callback_data="show_help",
                icon=AppleUI.ICONS["help"]
            )]
        ])
        
        await sent_message.edit(
            text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as exc:
        LOGGER.error("Auth failed for %s: %s", user_id, exc)
        
        # 错误消息
        error = AppleUI.create_error_message(
            "auth_failed",
            custom_message="授权代码无效或已过期"
        )
        
        error_text = AppleUI.format_message(
            title=error['title'],
            content=(
                f"{error['message']}\n\n"
                "请重新使用 `/auth` 命令获取新的授权链接。"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button(
                "重新授权",
                callback_data="auth_now",
                icon=AppleUI.ICONS["auth"]
            )]
        ])
        
        await sent_message.edit(
            error_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
    finally:
        pending_flows.pop(user_id, None)


auth_handler = _auth
revoke_handler = _revoke
token_handler = _token
