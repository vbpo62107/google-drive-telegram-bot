"""
Apple 风格的 Google Drive 授权界面
提供更友好的授权流程和视觉反馈
"""

import urllib.parse as urlparse
from dataclasses import dataclass
from typing import Dict, Optional

from google_auth_oauthlib.flow import Flow
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery

from bot import (
    G_DRIVE_CLIENT_ID,
    G_DRIVE_CLIENT_SECRET,
    LOGGER,
    OAUTH_SCOPE,
)
from bot.ui_apple_style import AppleUI
from bot.helpers.gdrive_utils.credentials_manager import credential_manager
from bot.helpers.sql_helper import gDriveDB
from bot.modules.drive_helper import invalidate_drive_instance


LOOPBACK_REDIRECT_URI = "http://127.0.0.1:53682/oauth2callback"


@dataclass
class PendingFlow:
    flow: Flow
    device: str
    state: Optional[str]


pending_flows_apple: Dict[int, PendingFlow] = {}


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
    if stripped.startswith("/"):
        return None, None
    if "code=" in stripped:
        parsed = urlparse.urlparse(stripped)
        query = urlparse.parse_qs(parsed.query)
        code = query.get("code", [None])[-1]
        state = query.get("state", [None])[-1]
        return code, state
    return stripped or None, None


@Client.on_message(filters.command(["auth_apple", "aa"]) & filters.private, group=0)
async def auth_apple_handler(client: Client, message):
    """
    Apple 风格的 Google Drive 授权命令
    """
    user_id = message.from_user.id
    text_content = message.text or ""
    parts = text_content.split(maxsplit=1)
    device_label = _sanitize_device_label(user_id, parts[1] if len(parts) > 1 else None)
    
    # 检查是否已授权
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
                    f"**设备**: `{device_label}`\n\n"
                    "您的 Google Drive 已成功连接\n\n"
                    "现在可以开始上传文件了！"
                ),
                footer="🔒 您的数据安全受到保护"
            )
            
            keyboard = AppleUI.create_keyboard([
                [
                    AppleUI.create_button("开始上传", callback_data="get_started", icon=AppleUI.ICONS["upload"]),
                    AppleUI.create_button("撤销授权", callback_data="revoke_auth", icon=AppleUI.ICONS["delete"])
                ],
                [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
            ])
            
            await message.reply_text(text, reply_markup=keyboard)
            return
        except Exception as exc:
            LOGGER.warning("Failed to refresh existing credentials for %s: %s", user_id, exc)
    
    # 生成授权 URL
    try:
        flow = _build_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        pending_flows_apple[user_id] = PendingFlow(flow=flow, device=device_label, state=state)
        
        LOGGER.info("Apple AuthURL generated for user: %s", user_id)
        
        # 授权引导消息
        text = AppleUI.format_message(
            title="Google Drive 授权",
            icon=AppleUI.ICONS["auth"],
            content=(
                "**步骤 1/2**: 授权访问\n\n"
                "1. 点击下方按钮打开 Google 授权页面\n"
                "2. 选择您的 Google 账户\n"
                "3. 允许访问权限\n"
                "4. 复制授权代码\n\n"
                "**步骤 2/2**: 提交代码\n\n"
                "将获取的授权代码直接发送给我"
            ),
            footer="🔒 我们不会存储您的 Google 密码"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("🔓  打开授权页面", url=auth_url)],
            [AppleUI.create_button("取消授权", callback_data="cancel_auth", icon=AppleUI.ICONS["cancel"])]
        ])
        
        await message.reply_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as exc:
        LOGGER.exception("Failed to generate auth URL for user %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message(
            "network_error",
            f"生成授权链接失败\n\n错误信息: `{str(exc)}`"
        )
        
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重试", callback_data="retry_auth", icon=AppleUI.ICONS["refresh"])]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)


@Client.on_message(filters.command(["revoke_apple", "ra"]) & filters.private, group=0)
async def revoke_apple_handler(client: Client, message):
    """
    Apple 风格的撤销授权命令
    """
    user_id = message.from_user.id
    
    # 确认提示
    text = AppleUI.format_message(
        title="撤销授权",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要撤销 Google Drive 授权吗？\n\n"
            "撤销后您将无法使用以下功能：\n"
            "• 上传文件到 Drive\n"
            "• 搜索和管理 Drive 文件\n"
            "• 克隆和删除文件\n\n"
            "您可以随时重新授权"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("确认撤销", callback_data="confirm_revoke", icon=AppleUI.ICONS["delete"]),
            AppleUI.create_button("取消", callback_data="cancel_revoke", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^confirm_revoke$"))
async def confirm_revoke_callback(client: Client, callback_query: CallbackQuery):
    """
    确认撤销授权
    """
    user_id = callback_query.from_user.id
    
    try:
        gDriveDB._clear(user_id)
        pending_flows_apple.pop(user_id, None)
        invalidate_drive_instance(user_id)
        
        LOGGER.info("Revoked Apple auth for user: %s", user_id)
        
        success = AppleUI.create_success_message(
            title="已撤销",
            message="Google Drive 授权已成功撤销",
            action="重新授权"
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"],
            footer="💡 您可以随时使用 `/auth_apple` 重新授权"
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重新授权", callback_data="start_auth", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("✅ 已撤销")
        
    except Exception as exc:
        LOGGER.exception("Failed to revoke auth for user %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message("network_error")
        text = AppleUI.format_message(
            title=error["title"],
            content=f"{error['message']}\n\n`{str(exc)}`"
        )
        
        await callback_query.message.edit_text(text)
        await callback_query.answer("❌ 撤销失败", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_revoke$"))
async def cancel_revoke_callback(client: Client, callback_query: CallbackQuery):
    """
    取消撤销授权
    """
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["success"],
        content="撤销操作已取消\n\n您的授权仍然有效"
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
    pending_flows_apple.pop(user_id, None)
    
    text = AppleUI.format_message(
        title="已取消",
        icon=AppleUI.ICONS["cancel"],
        content="授权流程已取消"
    )
    
    keyboard = AppleUI.create_keyboard([
        [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^revoke_auth$"))
async def revoke_auth_callback(client: Client, callback_query: CallbackQuery):
    """
    从已授权状态点击撤销按钮
    """
    user_id = callback_query.from_user.id
    
    text = AppleUI.format_message(
        title="撤销授权",
        icon=AppleUI.ICONS["warning"],
        content=(
            "确定要撤销 Google Drive 授权吗？\n\n"
            "撤销后您将无法使用上传和管理功能"
        )
    )
    
    keyboard = AppleUI.create_keyboard([
        [
            AppleUI.create_button("确认撤销", callback_data="confirm_revoke", icon=AppleUI.ICONS["delete"]),
            AppleUI.create_button("取消", callback_data="cancel_revoke", icon=AppleUI.ICONS["cancel"])
        ]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


@Client.on_message(filters.private & filters.incoming & filters.text, group=0)
async def token_apple_handler(client: Client, message):
    """
    处理用户提交的授权代码
    """
    user_id = message.from_user.id
    entry = pending_flows_apple.get(user_id)
    
    if not entry:
        return
    
    code, state = _parse_code(message.text or "")
    if not code:
        return
    
    if entry.state and state and state != entry.state:
        return
    
    # 显示处理中消息
    text = AppleUI.format_message(
        title="正在验证",
        icon=AppleUI.ICONS["processing"],
        content=(
            "正在验证您的授权代码...\n\n"
            "⏳ 请稍候"
        )
    )
    
    sent_message = await message.reply_text(text, quote=True)
    
    try:
        # 获取 token
        entry.flow.fetch_token(code=code)
        credentials = entry.flow.credentials
        payload, fingerprint = credential_manager.serialize_oauth(credentials)
        
        # 保存凭据
        gDriveDB.save_credentials(
            user_id,
            mode="oauth",
            payload=payload,
            fingerprint=fingerprint,
            device=entry.device,
        )
        gDriveDB.reset_failures(user_id)
        invalidate_drive_instance(user_id)
        
        LOGGER.info("Apple auth successful for user: %s", user_id)
        
        # 成功消息
        success = AppleUI.create_success_message(
            title="授权成功",
            message=(
                f"**设备**: `{entry.device}`\n\n"
                "Google Drive 已成功连接！\n\n"
                "现在可以开始上传文件了"
            )
        )
        
        text = AppleUI.format_message(
            title=success["title"],
            content=success["message"],
            footer="🔒 您的数据安全受到保护"
        )
        
        keyboard = AppleUI.create_keyboard([
            [
                AppleUI.create_button("开始上传", callback_data="get_started", icon=AppleUI.ICONS["upload"]),
                AppleUI.create_button("查看帮助", callback_data="show_help", icon=AppleUI.ICONS["help"])
            ],
            [AppleUI.create_button("返回主页", callback_data="back_home", icon=AppleUI.ICONS["home"])]
        ])
        
        await sent_message.edit_text(text, reply_markup=keyboard)
        
    except Exception as exc:
        LOGGER.error("Apple auth failed for user %s: %s", user_id, exc)
        
        error = AppleUI.create_error_message(
            "invalid_input",
            "授权代码无效或已过期\n\n请重新获取授权代码"
        )
        
        text = AppleUI.format_message(
            title=error["title"],
            content=error["message"]
        )
        
        keyboard = AppleUI.create_keyboard([
            [AppleUI.create_button("重新授权", callback_data="start_auth", icon=AppleUI.ICONS["auth"])],
            [AppleUI.create_button("取消", callback_data="cancel_auth", icon=AppleUI.ICONS["cancel"])]
        ])
        
        await sent_message.edit_text(text, reply_markup=keyboard)
        
    finally:
        pending_flows_apple.pop(user_id, None)


@Client.on_callback_query(filters.regex(r"^start_auth$"))
async def start_auth_callback(client: Client, callback_query: CallbackQuery):
    """
    从按钮启动授权流程
    """
    # 模拟 /auth_apple 命令
    from pyrogram.types import Message
    
    # 创建一个虚拟消息对象
    message = callback_query.message
    message.from_user = callback_query.from_user
    message.text = "/auth_apple"
    
    await auth_apple_handler(client, message)
    await callback_query.answer()
