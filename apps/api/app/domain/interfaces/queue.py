"""Queue provider port."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

JobT = TypeVar("JobT")


class QueueInterface(ABC, Generic[JobT]):
    """A first-in, first-out queue for application jobs."""

    @abstractmethod
    def enqueue(self, job: JobT) -> None:
        """Add a job to the end of the queue."""

    @abstractmethod
    def dequeue(self) -> Optional[JobT]:
        """Remove and return the next job, or ``None`` when empty."""

    @abstractmethod
    def peek(self) -> Optional[JobT]:
        """Return the next job without removing it, or ``None`` when empty."""

    @abstractmethod
    def clear(self) -> None:
        """Remove every queued job."""

    @abstractmethod
    def size(self) -> int:
        """Return the number of jobs currently queued."""
