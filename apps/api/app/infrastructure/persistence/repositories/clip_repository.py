"""SQLAlchemy repository for clip records."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.interfaces.repositories import ClipRepositoryInterface
from app.infrastructure.persistence.database import session_scope
from app.infrastructure.persistence.models.clip import Clip


class ClipRepository(ClipRepositoryInterface[Clip]):
    """Persist clip records through a transaction-scoped SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, clip: Clip) -> Clip:
        """Persist a clip and return it with its generated identifier."""
        with session_scope(self._session_factory) as session:
            session.add(clip)
            session.flush()
            session.refresh(clip)
        return clip

    def list_for_video(self, video_id: int) -> list[Clip]:
        """Return clips belonging to a video in deterministic identifier order."""
        with self._session_factory() as session:
            statement = select(Clip).where(Clip.video_id == video_id).order_by(Clip.id)
            return list(session.scalars(statement))
