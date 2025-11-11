import pickle
import threading
import time
from cachetools import TTLCache
from sqlalchemy import Column, Integer, LargeBinary
from bot.helpers.sql_helper import BASE, get_session


class gDriveCreds(BASE):
    __tablename__ = "gDrive"
    chat_id = Column(Integer, primary_key=True)
    credential_string = Column(LargeBinary)


    def __init__(self, chat_id):
        self.chat_id = chat_id


gDriveCreds.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()
_CACHE = TTLCache(maxsize=256, ttl=1800)


def _cache_key(chat_id):
    if isinstance(chat_id, bool):
        return chat_id
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return chat_id


def _cache_set(chat_id, creds):
    key = _cache_key(chat_id)
    if creds is None:
        _CACHE.pop(key, None)
    else:
        _CACHE[key] = (creds, time.time())


def _cache_get(chat_id):
    key = _cache_key(chat_id)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    return entry[0]


def _invalidate_drive(chat_id):
    try:
        from bot.modules.drive_helper import invalidate_drive_instance
    except Exception:
        return
    try:
        invalidate_drive_instance(chat_id)
    except Exception:
        pass


def _set(chat_id, credential_string):
    with INSERTION_LOCK:
        with get_session() as session:
            saved_cred = session.query(gDriveCreds).get(chat_id)
            if not saved_cred:
                saved_cred = gDriveCreds(chat_id)

            saved_cred.credential_string = pickle.dumps(credential_string)

            session.add(saved_cred)
            session.commit()

        _cache_set(chat_id, credential_string)

    _invalidate_drive(chat_id)


def search(chat_id):
    with INSERTION_LOCK:
        cached = _cache_get(chat_id)
        if cached is not None:
            return cached

        with get_session() as session:
            saved_cred = session.query(gDriveCreds).get(chat_id)
            creds = None
            if saved_cred is not None:
                creds = pickle.loads(saved_cred.credential_string)

        _cache_set(chat_id, creds)
        return creds


def exists(chat_id: str) -> bool:
    with INSERTION_LOCK:
        with get_session() as session:
            return session.query(gDriveCreds.chat_id).filter_by(chat_id=chat_id).scalar() is not None


def _clear(chat_id):
    with INSERTION_LOCK:
        with get_session() as session:
            saved_cred = session.query(gDriveCreds).get(chat_id)
            if saved_cred:
                session.delete(saved_cred)
                session.commit()

        _cache_set(chat_id, None)

    _invalidate_drive(chat_id)
