"""Thread-safe in-memory queue adapter."""

from collections import deque
from threading import Lock
from typing import Generic, Optional

from app.domain.interfaces.queue import JobT, QueueInterface


class LocalQueueProvider(QueueInterface[JobT], Generic[JobT]):
    """A process-local FIFO queue suitable for local development only."""

    def __init__(self) -> None:
        self._jobs: deque[JobT] = deque()
        self._lock = Lock()

    def enqueue(self, job: JobT) -> None:
        """Add a job to the queue."""
        with self._lock:
            self._jobs.append(job)

    def dequeue(self) -> Optional[JobT]:
        """Remove and return the next job, if one is available."""
        with self._lock:
            return self._jobs.popleft() if self._jobs else None

    def peek(self) -> Optional[JobT]:
        """Return the next job without removing it, if one is available."""
        with self._lock:
            return self._jobs[0] if self._jobs else None

    def clear(self) -> None:
        """Remove all queued jobs."""
        with self._lock:
            self._jobs.clear()

    def size(self) -> int:
        """Return the current queue size."""
        with self._lock:
            return len(self._jobs)
