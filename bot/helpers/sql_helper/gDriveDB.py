import pickle
import threading
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


def _set(chat_id, credential_string):
    with INSERTION_LOCK:
        with get_session() as session:
            saved_cred = session.query(gDriveCreds).get(chat_id)
            if not saved_cred:
                saved_cred = gDriveCreds(chat_id)

            saved_cred.credential_string = pickle.dumps(credential_string)

            session.add(saved_cred)
            session.commit()


def search(chat_id):
    with INSERTION_LOCK:
        with get_session() as session:
            saved_cred = session.query(gDriveCreds).get(chat_id)
            creds = None
            if saved_cred is not None:
                creds = pickle.loads(saved_cred.credential_string)
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
