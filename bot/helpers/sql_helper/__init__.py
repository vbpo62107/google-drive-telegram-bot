from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query, sessionmaker

from bot import DATABASE_URL, LOGGER


BASE = declarative_base()

try:
    ENGINE = create_engine(DATABASE_URL)
except ValueError:
    LOGGER.error("Invalid DATABASE_URL : Exiting now.")
    raise SystemExit(1)

SESSION_FACTORY = sessionmaker(bind=ENGINE, autoflush=False)
_INITIALIZED = False


def start() -> sessionmaker:
    """
    Initialize database schema and return the shared session factory.

    This function is safe to call multiple times; tables are created
    against the shared ENGINE using SQLAlchemy's create_all metadata API.
    """
    global _INITIALIZED
    if not _INITIALIZED:
        BASE.metadata.create_all(bind=ENGINE)
        _INITIALIZED = True
    return SESSION_FACTORY


# ---------------------------------------------------------------------------
# SQLAlchemy 2.x compatibility helpers
# ---------------------------------------------------------------------------
# SQLAlchemy 2.x removes Query.get(); existing code still calls
# session.query(Model).get(pk). Provide a small shim that forwards to
# Session.get() when running under SQLAlchemy 2.x while keeping the
# public API unchanged.

if not hasattr(Query, "get"):
    def _legacy_query_get(self, ident):
        try:
            entity = self.column_descriptions[0].get("entity")
        except Exception:
            entity = None
        if entity is None:
            raise AttributeError("Query.get() fallback could not determine entity")
        return self.session.get(entity, ident)

    Query.get = _legacy_query_get  # type: ignore[attr-defined]


@contextmanager
def get_session():
    session = start()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
