from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func

from bot.helpers.sql_helper import BASE, get_session


class OneOneFiveAuth(BASE):
    __tablename__ = "oneonefive_auth"

    user_id = Column(BigInteger, primary_key=True, index=True)
    cookies = Column(Text, nullable=True)
    token = Column(Text, nullable=True)
    app_id = Column(String(64), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _to_dict(record: OneOneFiveAuth) -> dict:
    return {
        "user_id": record.user_id,
        "cookies": record.cookies,
        "token": record.token,
        "app_id": record.app_id,
        "updated_at": record.updated_at,
    }


def save_oneonefive_auth(
    user_id: int,
    cookies: Optional[str] = None,
    token: Optional[str] = None,
    app_id: Optional[str | int] = None,
) -> dict:
    """
    保存或更新 115 授权信息。

    :param user_id: Telegram 用户 ID
    :param cookies: 115 Cookies 字符串
    :param token: 115 的 access_token 或 refresh_token
    :param app_id: 使用 token 登录时的 AppID
    :return: 序列化后的授权记录
    """
    cookies = _clean_value(cookies)
    token = _clean_value(token)
    app_id_str = _clean_value(str(app_id)) if app_id is not None else None
    if not cookies and not token:
        raise ValueError("至少需要提供 cookies 或 token 之一")

    with get_session() as session:
        record = session.query(OneOneFiveAuth).get(user_id)
        if not record:
            record = OneOneFiveAuth(user_id=user_id)
        record.cookies = cookies
        record.token = token
        record.app_id = app_id_str
        record.updated_at = datetime.utcnow()
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_dict(record)


def get_oneonefive_auth(user_id: int) -> Optional[dict]:
    with get_session() as session:
        record = session.query(OneOneFiveAuth).get(user_id)
        if not record:
            return None
        return _to_dict(record)


def remove_oneonefive_auth(user_id: int) -> bool:
    with get_session() as session:
        record = session.query(OneOneFiveAuth).get(user_id)
        if not record:
            return False
        session.delete(record)
        session.commit()
        return True
