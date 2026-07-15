from collections.abc import Generator

import pytest
from app.infrastructure.persistence.database import create_database_engine, create_session_factory
from app.infrastructure.persistence.models import Clip, Job, Settings, Video  # noqa: F401
from app.infrastructure.persistence.models.base import Base
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def session_factory(tmp_path) -> Generator[sessionmaker[Session], None, None]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield create_session_factory(engine)
    Base.metadata.drop_all(engine)
    engine.dispose()
