"""SQLAlchemy repository for video records."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.interfaces.repositories import VideoRepositoryInterface
from app.infrastructure.persistence.database import session_scope
from app.infrastructure.persistence.models.video import Video


class VideoRepository(VideoRepositoryInterface[Video]):
    """Persist video records through a transaction-scoped SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, video: Video) -> Video:
        """Persist a video and return it with its generated identifier."""
        with session_scope(self._session_factory) as session:
            session.add(video)
            session.flush()
            session.refresh(video)
        return video

    def get(self, video_id: int) -> Optional[Video]:
        """Return a video by identifier."""
        with self._session_factory() as session:
            return session.get(Video, video_id)

    def list(self) -> list[Video]:
        """Return all videos in deterministic identifier order."""
        with self._session_factory() as session:
            return list(session.scalars(select(Video).order_by(Video.id)))
