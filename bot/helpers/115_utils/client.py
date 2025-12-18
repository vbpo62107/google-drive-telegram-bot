from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from p115client import P115Client, P115Error, P115OpenClient, check_response

from bot import LOGGER


class OneOneFiveError(Exception):
    """基础异常。"""


class OneOneFiveAuthError(OneOneFiveError):
    """授权相关异常。"""


class OneOneFiveUploadError(OneOneFiveError):
    """上传或分享异常。"""


@dataclass
class ShareInfo:
    file_id: str
    share_url: str
    share_code: Optional[str] = None
    receive_code: Optional[str] = None


class OneOneFiveClient:
    """
    115 客户端封装，负责登录、上传并返回分享链接。
    """

    def __init__(
        self,
        *,
        cookies: Optional[str] = None,
        token: Optional[str] = None,
        app_id: Optional[str | int] = None,
    ) -> None:
        self._client = self._build_client(cookies=cookies, token=token, app_id=app_id)

    def upload_and_share(self, file_path: str, pid: int | str = 0, filename: Optional[str] = None) -> ShareInfo:
        file_id = self._upload_file(file_path=file_path, pid=pid, filename=filename)
        return self._share_file(file_id)

    def _build_client(
        self,
        *,
        cookies: Optional[str],
        token: Optional[str],
        app_id: Optional[str | int],
    ) -> P115Client:
        if cookies:
            try:
                LOGGER.info("使用 Cookies 登录 115")
                return P115Client(cookies=cookies, check_for_relogin=True, ensure_cookies=True)
            except Exception as exc:
                raise OneOneFiveAuthError(f"115 Cookies 登录失败: {exc}") from exc

        if not token:
            raise OneOneFiveAuthError("缺少 115 授权信息，无法初始化客户端")

        login_target: str | int = token
        if app_id is not None and not token:
            login_target = app_id

        try:
            LOGGER.info("使用 token 登录 115（app_id=%s）", app_id)
            instance = P115Client.__new__(P115Client)
            client = P115OpenClient.init(app_id_or_refresh_token=login_target, console_qrcode=False, instance=instance)
            if not isinstance(client, P115Client):
                client.__class__ = P115Client
            return client
        except Exception as exc:
            raise OneOneFiveAuthError(f"115 token 登录失败: {exc}") from exc

    def _upload_file(self, *, file_path: str, pid: int | str, filename: Optional[str]) -> str:
        path = Path(file_path)
        if not path.is_file():
            raise OneOneFiveUploadError(f"待上传文件不存在或不可读: {file_path}")
        resolved_name = filename or path.name

        try:
            resp = self._client.upload_file(file=str(path), pid=pid, filename=resolved_name)
            check_response(resp)
        except P115Error as exc:
            raise OneOneFiveUploadError(f"115 上传失败: {exc}") from exc
        except Exception as exc:
            raise OneOneFiveUploadError(f"调用 115 上传接口时出错: {exc}") from exc

        file_id = self._extract_file_id(resp)
        if not file_id:
            raise OneOneFiveUploadError("上传结果缺少文件 ID")
        return str(file_id)

    def _share_file(self, file_id: str) -> ShareInfo:
        try:
            resp = self._client.share_send(file_id)
            check_response(resp)
        except P115Error as exc:
            raise OneOneFiveUploadError(f"创建 115 分享链接失败: {exc}") from exc
        except Exception as exc:
            raise OneOneFiveUploadError(f"调用 115 分享接口时出错: {exc}") from exc

        share_url, share_code, receive_code = self._extract_share_info(resp)
        if not share_url:
            share_url = self._build_share_url(share_code, receive_code)
        if not share_url:
            raise OneOneFiveUploadError("分享链接生成失败")
        return ShareInfo(file_id=str(file_id), share_url=share_url, share_code=share_code, receive_code=receive_code)

    @staticmethod
    def _extract_file_id(resp: dict[str, Any]) -> Optional[str]:
        candidates = (
            resp.get("file_id"),
            resp.get("fileid"),
            resp.get("id"),
        )
        for candidate in candidates:
            if candidate:
                return str(candidate)

        data = resp.get("data") or {}
        for key in ("file_id", "fileid", "id"):
            value = data.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _extract_share_info(resp: dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
        data = resp.get("data") or {}
        share_url = resp.get("share_url") or data.get("share_url") or data.get("url") or data.get("short_url")
        share_code = (
            resp.get("share_code") or data.get("share_code") or data.get("pick_code") or data.get("pickcode")
        )
        receive_code = resp.get("receive_code") or data.get("receive_code") or data.get("passwd")
        return share_url, share_code, receive_code

    @staticmethod
    def _build_share_url(share_code: Optional[str], receive_code: Optional[str]) -> Optional[str]:
        if not share_code:
            return None
        base = f"https://115.com/s/{share_code}"
        if receive_code:
            return f"{base}?password={receive_code}"
        return base
