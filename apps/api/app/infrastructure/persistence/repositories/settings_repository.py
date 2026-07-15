"""SQLAlchemy repository for settings records."""

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.domain.interfaces.repositories import SettingsRepositoryInterface
from app.infrastructure.persistence.database import session_scope
from app.infrastructure.persistence.models.settings import Settings


class SettingsRepository(SettingsRepositoryInterface[Settings]):
    """Persist settings records through a transaction-scoped SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, settings: Settings) -> Settings:
        """Insert or update a settings record and return its persistent form."""
        with session_scope(self._session_factory) as session:
            persisted = session.merge(settings)
            session.flush()
            session.refresh(persisted)
        return persisted

    def get(self, settings_id: int) -> Optional[Settings]:
        """Return settings by identifier."""
        with self._session_factory() as session:
            return session.get(Settings, settings_id)
