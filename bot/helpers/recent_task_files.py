from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from bot import LOGGER
from bot.helpers.sql_helper import get_session
from bot.helpers.sql_helper.mirror_tasks import MirrorTask, MirrorTaskStatus
from bot.helpers.sql_helper.recent_task_files import RecentTaskFile

MAX_RECENT_FILES_PER_USER = 3


@dataclass
class RecentFileInfo:
    task_id: int
    user_id: int
    file_name: str
    path: Path
    created_at: datetime


def _remove_path_if_exists(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
            parent = path.parent
            if parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    pass
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to remove cached file %s: %s", path, exc)


def _record_to_info(record: RecentTaskFile) -> Optional[RecentFileInfo]:
    path = Path(record.file_path)
    if not path.is_file():
        with get_session() as session:
            try:
                session.query(RecentTaskFile).filter(RecentTaskFile.id == record.id).delete()
                session.commit()
            except Exception:  # noqa: BLE001
                session.rollback()
        return None
    return RecentFileInfo(
        task_id=record.task_id,
        user_id=record.user_id,
        file_name=record.file_name,
        path=path,
        created_at=record.created_at,
    )


def _prunable(record: RecentTaskFile, active_task_ids: set[int]) -> bool:
    if record.task_id in active_task_ids:
        return False
    path = Path(record.file_path)
    return path.is_file() or not path.exists()


def _collect_active_task_ids(session) -> set[int]:
    active_statuses = {
        MirrorTaskStatus.PENDING.value,
        MirrorTaskStatus.RUNNING.value,
        MirrorTaskStatus.PAUSED.value,
    }
    active_tasks: Iterable[MirrorTask] = session.query(MirrorTask).filter(MirrorTask.status.in_(active_statuses)).all()
    return {task.id for task in active_tasks}


def record_recent_task_file(task_id: int, user_id: int, file_name: str, file_path: str) -> RecentFileInfo:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        record = (
            session.query(RecentTaskFile)
            .filter(RecentTaskFile.task_id == task_id)
            .one_or_none()
        )
        if record:
            record.file_name = file_name
            record.file_path = file_path
            record.user_id = user_id
            record.created_at = now
        else:
            record = RecentTaskFile(
                task_id=task_id,
                user_id=user_id,
                file_name=file_name,
                file_path=file_path,
                created_at=now,
            )
        session.add(record)
        session.commit()

        _prune_for_user(session, user_id)
        session.refresh(record)
        info = _record_to_info(record)
        if info:
            return info
        raise FileNotFoundError(f"Cached file not found for task {task_id}: {file_path}")


def _prune_for_user(session, user_id: int) -> None:
    records: list[RecentTaskFile] = (
        session.query(RecentTaskFile)
        .filter(RecentTaskFile.user_id == user_id)
        .order_by(RecentTaskFile.created_at.desc(), RecentTaskFile.id.desc())
        .all()
    )
    if len(records) <= MAX_RECENT_FILES_PER_USER:
        return

    active_task_ids = _collect_active_task_ids(session)
    stale_records = records[MAX_RECENT_FILES_PER_USER :]
    for stale in stale_records:
        if not _prunable(stale, active_task_ids):
            continue
        _remove_path_if_exists(Path(stale.file_path))
        try:
            session.delete(stale)
            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            LOGGER.warning("Failed to prune cached file for user %s (task %s): %s", user_id, stale.task_id, exc)


def get_recent_file_by_task(task_id: int) -> Optional[RecentFileInfo]:
    with get_session() as session:
        record = (
            session.query(RecentTaskFile)
            .filter(RecentTaskFile.task_id == task_id)
            .one_or_none()
        )
    if not record:
        return None
    return _record_to_info(record)


def get_latest_file_for_user(user_id: int) -> Optional[RecentFileInfo]:
    with get_session() as session:
        record = (
            session.query(RecentTaskFile)
            .filter(RecentTaskFile.user_id == user_id)
            .order_by(RecentTaskFile.created_at.desc(), RecentTaskFile.id.desc())
            .first()
        )
    if not record:
        return None
    return _record_to_info(record)
