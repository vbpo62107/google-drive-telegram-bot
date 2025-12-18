from __future__ import annotations

from pathlib import Path
from typing import Optional

from importlib import import_module

from bot import LOGGER
from bot.helpers.sql_helper.oneonefive_db import get_oneonefive_auth

_client = import_module("bot.helpers.115_utils.client")
OneOneFiveAuthError = _client.OneOneFiveAuthError
OneOneFiveClient = _client.OneOneFiveClient
OneOneFiveUploadError = _client.OneOneFiveUploadError
ShareInfo = _client.ShareInfo


def upload_to_115_for_user(
    user_id: int,
    file_path: str,
    pid: int | str = 0,
    filename: Optional[str] = None,
) -> ShareInfo:
    """
    读取用户授权，上传文件到 115 并返回分享信息。

    :param user_id: Telegram 用户 ID
    :param file_path: 待上传的本地文件路径
    :param pid: 115 目标目录 ID 或 pickcode
    :param filename: 自定义文件名
    :return: ShareInfo 包含分享链接和分享码
    """
    if not Path(file_path).is_file():
        raise OneOneFiveUploadError(f"文件不存在: {file_path}")

    auth = get_oneonefive_auth(user_id)
    if not auth:
        raise OneOneFiveAuthError(f"未找到用户 {user_id} 的 115 授权信息")

    client = OneOneFiveClient(cookies=auth.get("cookies"), token=auth.get("token"), app_id=auth.get("app_id"))
    LOGGER.info("用户 %s 正在向 115 上传文件 %s 至目录 %s", user_id, file_path, pid)
    return client.upload_and_share(file_path=file_path, pid=pid, filename=filename)
