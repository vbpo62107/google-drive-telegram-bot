import json
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, Column, Integer, Text

from bot.helpers.sql_helper import BASE, get_session


class KeywordMonitor(BASE):
    __tablename__ = "keyword_monitors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    keywords = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)


KeywordMonitor.__table__.create(checkfirst=True)


def _serialize_keywords(keywords: List[str]) -> str:
    unique = []
    seen = set()
    for keyword in keywords:
        cleaned = keyword.strip()
        if not cleaned:
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        unique.append(cleaned)
    return json.dumps(unique, ensure_ascii=False)


def _deserialize_keywords(raw: str) -> List[str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = []
    if isinstance(data, list):
        return [str(item) for item in data if str(item).strip()]
    return []


def _to_dict(record: KeywordMonitor) -> dict:
    return {
        "id": record.id,
        "channel_id": record.channel_id,
        "keywords": _deserialize_keywords(record.keywords),
        "enabled": record.enabled,
    }


def create_monitor(channel_id: int, keywords: List[str], enabled: bool = True) -> dict:
    payload = _serialize_keywords(keywords)
    with get_session() as session:
        record = KeywordMonitor(channel_id=channel_id, keywords=payload, enabled=enabled)
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_dict(record)


def list_monitors() -> List[dict]:
    with get_session() as session:
        records = session.query(KeywordMonitor).order_by(KeywordMonitor.id.asc()).all()
        return [_to_dict(record) for record in records]


def get_monitor(monitor_id: int) -> Optional[dict]:
    with get_session() as session:
        record = session.query(KeywordMonitor).get(monitor_id)
        if not record:
            return None
        return _to_dict(record)


def update_monitor(monitor_id: int, keywords: Optional[List[str]] = None, enabled: Optional[bool] = None) -> Optional[dict]:
    with get_session() as session:
        record = session.query(KeywordMonitor).get(monitor_id)
        if not record:
            return None
        if keywords is not None:
            record.keywords = _serialize_keywords(keywords)
        if enabled is not None:
            record.enabled = enabled
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_dict(record)


def delete_monitor(monitor_id: int) -> bool:
    with get_session() as session:
        record = session.query(KeywordMonitor).get(monitor_id)
        if not record:
            return False
        session.delete(record)
        session.commit()
        return True


def toggle_monitor(monitor_id: int) -> Optional[dict]:
    with get_session() as session:
        record = session.query(KeywordMonitor).get(monitor_id)
        if not record:
            return None
        record.enabled = not record.enabled
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_dict(record)


def get_enabled_monitors_by_channel(channel_id: int) -> List[dict]:
    with get_session() as session:
        records = (
            session.query(KeywordMonitor)
            .filter(KeywordMonitor.channel_id == channel_id, KeywordMonitor.enabled.is_(True))
            .all()
        )
        return [_to_dict(record) for record in records]
