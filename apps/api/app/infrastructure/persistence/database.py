"""Database engine and session-factory configuration."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./data/gameplay.db"


def get_database_url() -> str:
    """Return the configured database URL, defaulting to local SQLite."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_database_engine(database_url: Optional[str] = None) -> Engine:
    """Create an SQLAlchemy engine configured for the selected database."""
    url = database_url or get_database_url()
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        database_path = Path(url[len("sqlite:///") :])
        database_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory with explicit transaction boundaries."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional session and guarantee cleanup on every path."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
