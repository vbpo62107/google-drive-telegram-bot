from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, Text

from bot.helpers.sql_helper import BASE


class RecentTaskFile(BASE):
    __tablename__ = "recent_task_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, unique=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
