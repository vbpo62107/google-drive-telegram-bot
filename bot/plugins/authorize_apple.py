"""
Apple 风格的 Google Drive 授权模块
提供更友好的授权体验
"""

import urllib.parse as urlparse
from dataclasses import dataclass
from typing import Dict, Optional

from google_auth_oauthlib.flow import Flow
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot import (
    G_DRIVE_CLIENT_ID,
    G_DRIVE_CLIENT_SECRET,
    LOGGER,
    OAUTH_SCOPE,
)
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
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
    # 忽略机器人命令
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


@Client.on_message(filters.private & filters.incoming & filters.command(["auth", "authorize"]), group=0)
async def auth_apple(client: Client, message):
    """
    Apple 风格的授权命令
    """
    user_id = message.from_user.id
    text = message.text or ""
    parts = text.split(maxsplit=1)
    device_label = _sanitize_device_label(user_id, parts[1] if len(parts) > 1 else None)
    
    # 检查是否已经授权
    record = gDriveDB.search(user_id)
    if record and record.is_oauth():
        try:
            credential_manager.build_credentials(user_id, record)
            gDriveDB.reset_failures(user_id)
            invalidate_drive_instance(user_id)
            
            # 已授权消息
            text = AppleUI.format_message(
                title="已授权",
                icon=AppleUI.ICONS["success"],
                content=(
                    "您的 Google Drive 账户已经授权。\n\n"
                    f"📱 设备：`{record.device or '默认'}`\n\n"
                    "如需重新授权，请先使用 `/revoke` 撤销当前授权。"
                )
            )
            
            keyboard = AppleUI.create_keyboard([
                [
                    AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["cancel"]),
                    AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])
                ]
            ])
            
            await message.reply_text(text, reply_markup=keyboard, quote=True)
            return
        except Exception as exc:
            LOGGER.warning("Failed to refresh existing credentials for %s: %s", user_id, exc)
    
    # 开始新的授权流程
    try:
        flow = _build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        pending_flows[user_id] = PendingFlow(flow=flow, device=device_label, state=state)
        
        LOGGER.info("Auth flow started for user %s", user_id)
        
        # Apple 风格的授权指引
        text = AppleUI.format_message(
            title="Google Drive 授权",
            icon=AppleUI.ICONS["auth"],
            content=(
                "**步骤 1：获取授权**\n"
                "点击下方按钮打开 Google 授权页面\n\n"
                "**步骤 2：登录并授权**\n"
                "在浏览器中登录并允许权限\n\n"
                "**步骤 3：复制代码**\n"
                "复制授权代码并发送给我\n\n"
                "🔒 您的数据安全与隐私是我们的首要任务"
            ),
            footer="⚠️ 请勿分享授权代码给他人"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("🔓  打开授权页面", url=auth_url)],
            [AppleUI.create_button("取消", callback_data="cancel_auth", icon=AppleUI.ICONS["cancel"])]
        ])
        
        await message.reply_text(
            text,
            reply_markup=keyboard,
            quote=True,
            disable_web_page_preview=True
        )
        
    except Exception as exc:
        LOGGER.exception("Auth flow failed for %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message(
            "auth_failed",
            custom_message=f"初始化授权失败\n\n错误：`{str(exc)}`"
        )
        
        text = f"{error['title']}\n\n{error['message']}"
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重试", callback_data="retry_auth", icon=AppleUI.ICONS["refresh"])],
            [AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard, quote=True)


@Client.on_message(filters.private & filters.incoming & filters.command(["revoke"]), group=0)
async def revoke_apple(client: Client, message):
    """
    Apple 风格的撤销授权命令
    """
    user_id = message.from_user.id
    
    # 检查是否有授权
    record = gDriveDB.search(user_id)
    if not record:
        text = AppleUI.format_message(
            title="未找到授权",
            icon=AppleUI.ICONS["info"],
            content=(
                "您尚未授权 Google Drive 账户。\n\n"
                "使用 `/auth` 命令开始授权。"
            )
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("立即授权", callback_data="auth_now", icon=AppleUI.ICONS["auth"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard, quote=True)
        return
    
    # 确认撤销
    text = AppleUI.format_message(
        title="撤销授权",
        icon=AppleUI.ICONS["warning"],
        content=(
            f"您确定要撤销 Google Drive 授权吗？\n\n"
            f"📱 设备：`{record.device or '默认'}`\n\n"
            "撤销后您将无法使用 Google Drive 功能，\n"
            "需要重新授权才能继续使用。"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("确认撤销", callback_data="confirm_revoke", icon=AppleUI.ICONS["delete"])],
        [AppleUI.create_button("取消", callback_data="cancel_revoke", icon=AppleUI.ICONS["cancel"])]
    ])
    
    await message.reply_text(text, reply_markup=keyboard, quote=True)


@Client.on_message(filters.private & filters.incoming & filters.text, group=2)
async def token_handler_apple(client: Client, message):
    """
    处理用户发送的授权代码
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
    processing_text = AppleUI.format_message(
        title="正在验证",
        icon=AppleUI.ICONS["processing"],
        content="正在验证您的授权代码...\n\n请稍候"
    )
    
    sent_message = await message.reply_text(
        processing_text,
        quote=True,
        disable_web_page_preview=True
    )
    
    try:
        # 获取凭证
        entry.flow.fetch_token(code=code)
        credentials = entry.flow.credentials
        payload, fingerprint = credential_manager.serialize_oauth(credentials)
        
        # 保存凭证
        gDriveDB.save_credentials(
            user_id,
            mode="oauth",
            payload=payload,
            fingerprint=fingerprint,
            device=entry.device,
        )
        gDriveDB.reset_failures(user_id)
        invalidate_drive_instance(user_id)
        
        LOGGER.info("Auth successful for user %s", user_id)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="授权成功",
            message=(
                "您的 Google Drive 已成功连接！\n\n"
                f"📱 设备：`{entry.device}`\n\n"
                "现在您可以：\n"
                "• 上传文件到 Google Drive\n"
                "• 管理您的云端文件\n"
                "• 使用所有 Drive 功能"
            ),
            action="开始使用"
        )
        
        text = f"{success['title']}\n\n{success['message']}"
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("📤  开始上传", callback_data="get_started")],
            [
                AppleUI.create_button("设置文件夹", callback_data="set_folder", icon=AppleUI.ICONS["folder"]),
                AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])
            ]
        ])
        
        await sent_message.edit_text(text, reply_markup=keyboard)
        
    except Exception as exc:
        LOGGER.error("Auth failed for %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message(
            "auth_failed",
            custom_message=f"授权代码无效或已过期\n\n错误：`{str(exc)}`"
        )
        
        text = f"{error['title']}\n\n{error['message']}"
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重新授权", callback_data="retry_auth", icon=AppleUI.ICONS["refresh"])],
            [AppleUI.create_button("帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])]
        ])
        
        await sent_message.edit_text(text, reply_markup=keyboard)
        
    finally:
        pending_flows.pop(user_id, None)


@Client.on_callback_query(filters.regex(r"^confirm_revoke$"))
async def confirm_revoke_callback(client: Client, callback_query: CallbackQuery):
    """
    确认撤销授权
    """
    user_id = callback_query.from_user.id
    
    try:
        gDriveDB._clear(user_id)
        pending_flows.pop(user_id, None)
        invalidate_drive_instance(user_id)
        
        LOGGER.info("Auth revoked for user %s", user_id)
        
        success = AppleUI.create_success_message(
            title="撤销成功",
            message=(
                "Google Drive 授权已撤销。\n\n"
                "您的账户已断开连接，\n"
                "如需继续使用，请重新授权。"
            )
        )
        
        text = f"{success['title']}\n\n{success['message']}"
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重新授权", callback_data="retry_auth", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("已撤销授权")
        
    except Exception as exc:
        LOGGER.exception("Revoke failed for %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message(
            "permission_denied",
            custom_message=f"撤销失败\n\n错误：`{str(exc)}`"
        )
        
        await callback_query.message.edit_text(f"{error['title']}\n\n{error['message']}")
        await callback_query.answer("撤销失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_revoke$"))
async def cancel_revoke_callback(client: Client, callback_query: CallbackQuery):
    """
    取消撤销授权
    """
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["success"],
        content="撤销操作已取消。\n\n您的授权仍然有效。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^(retry_auth|revoke_auth)$"))
async def auth_action_callback(client: Client, callback_query: CallbackQuery):
    """
    处理授权相关操作
    """
    action = callback_query.data
    
    if action == "retry_auth":
        text = AppleUI.format_message(
            title="开始授权",
            icon=AppleUI.ICONS["auth"],
            content="请使用以下命令开始授权：\n\n`/auth`"
        )
    else:  # revoke_auth
        text = AppleUI.format_message(
            title="撤销授权",
            icon=AppleUI.ICONS["warning"],
            content="请使用以下命令撤销授权：\n\n`/revoke`"
        )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^cancel_auth$"))
async def cancel_auth_callback(client: Client, callback_query: CallbackQuery):
    """
    取消授权流程
    """
    user_id = callback_query.from_user.id
    pending_flows.pop(user_id, None)
    
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["info"],
        content="授权流程已取消。\n\n如需授权，请再次使用 `/auth` 命令。"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer("已取消授权")


# 导出处理器
auth_handler_apple = auth_apple
revoke_handler_apple = revoke_apple
token_handler_apple = token_handler_apple
