from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text

from bot.helpers.sql_helper import BASE


class MirrorTaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MirrorTask(BASE):
    __tablename__ = "mirror_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=True)
    url = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True, default=MirrorTaskStatus.PENDING.value)
    stage = Column(String(64), nullable=False, default="等待")
    processed_bytes = Column(BigInteger, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)
    speed = Column(Float, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error = Column(Text, nullable=True)
    drive_link = Column(Text, nullable=True)
    paused = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


