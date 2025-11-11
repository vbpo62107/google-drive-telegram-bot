from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from bot import DATABASE_URL, LOGGER


BASE = declarative_base()


def start() -> sessionmaker:
    try:
        engine = create_engine(DATABASE_URL)
        BASE.metadata.bind = engine
        BASE.metadata.create_all(engine)
        return sessionmaker(bind=engine, autoflush=False)
    except ValueError:
        LOGGER.error('Invalid DATABASE_URL : Exiting now.')
        exit(1)


SESSION_FACTORY = start()


@contextmanager
def get_session():
    session = SESSION_FACTORY()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
