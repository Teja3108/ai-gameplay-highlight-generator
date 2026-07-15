"""SQLAlchemy repository for job records."""

from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from app.domain.interfaces.repositories import JobRepositoryInterface
from app.infrastructure.persistence.database import session_scope
from app.infrastructure.persistence.models.job import Job


class JobRepository(JobRepositoryInterface[Job]):
    """Persist job records through a transaction-scoped SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, job: Job) -> Job:
        """Persist a job and return it with its generated identifier."""
        with session_scope(self._session_factory) as session:
            session.add(job)
            session.flush()
            session.refresh(job)
        return job

    def get(self, job_id: int) -> Optional[Job]:
        """Return a job by identifier."""
        with self._session_factory() as session:
            return session.get(Job, job_id)
