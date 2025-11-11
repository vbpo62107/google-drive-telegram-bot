from sqlalchemy import Column, String, Numeric
from bot.helpers.sql_helper import BASE, get_session


class ParentID(BASE):
    __tablename__ = "ParentID"
    chat_id = Column(Numeric, primary_key=True)
    parent_id = Column(String)


    def __init__(self, chat_id, parent_id):
        self.chat_id = chat_id
        self.parent_id = parent_id

ParentID.__table__.create(checkfirst=True)


def search_parent(chat_id):
    with get_session() as session:
        parent_id = session.query(ParentID).with_entities(ParentID.parent_id).filter_by(chat_id=chat_id).scalar()
        return parent_id if parent_id is not None else 'root'


def _set(chat_id, parent_id):
    with get_session() as session:
        adder = session.query(ParentID).get(chat_id)
        if adder:
            adder.parent_id = parent_id
        else:
            adder = ParentID(
                chat_id,
                parent_id
            )
        session.add(adder)
        session.commit()


def _clear(chat_id):
    with get_session() as session:
        rem = session.query(ParentID).get(chat_id)
        if rem:
            session.delete(rem)
            session.commit()
