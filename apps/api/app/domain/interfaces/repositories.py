"""Repository ports for persistence-backed application entities."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

EntityT = TypeVar("EntityT")


class VideoRepositoryInterface(ABC, Generic[EntityT]):
    """Persistence operations available for videos."""

    @abstractmethod
    def add(self, video: EntityT) -> EntityT:
        """Persist and return a video."""

    @abstractmethod
    def get(self, video_id: int) -> Optional[EntityT]:
        """Return a video by identifier."""

    @abstractmethod
    def list(self) -> list[EntityT]:
        """Return videos ordered by identifier."""


class ClipRepositoryInterface(ABC, Generic[EntityT]):
    """Persistence operations available for clips."""

    @abstractmethod
    def add(self, clip: EntityT) -> EntityT:
        """Persist and return a clip."""

    @abstractmethod
    def list_for_video(self, video_id: int) -> list[EntityT]:
        """Return clips for a video ordered by identifier."""


class JobRepositoryInterface(ABC, Generic[EntityT]):
    """Persistence operations available for jobs."""

    @abstractmethod
    def add(self, job: EntityT) -> EntityT:
        """Persist and return a job."""

    @abstractmethod
    def get(self, job_id: int) -> Optional[EntityT]:
        """Return a job by identifier."""


class SettingsRepositoryInterface(ABC, Generic[EntityT]):
    """Persistence operations available for application settings."""

    @abstractmethod
    def save(self, settings: EntityT) -> EntityT:
        """Persist and return settings."""

    @abstractmethod
    def get(self, settings_id: int) -> Optional[EntityT]:
        """Return settings by identifier."""
