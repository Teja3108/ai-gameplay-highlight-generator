"""Application composition root and dependency registry."""

import os
from pathlib import Path
from typing import Any, Optional, TypeVar, cast

from app.domain.interfaces.auth import AuthProvider
from app.domain.interfaces.queue import QueueInterface
from app.domain.interfaces.storage import StorageInterface
from app.infrastructure.auth.local_auth_provider import LocalAuthProvider
from app.infrastructure.queue.local_queue_provider import LocalQueueProvider
from app.infrastructure.storage.local_storage_provider import LocalStorageProvider

DependencyT = TypeVar("DependencyT")


class DependencyContainer:
    """Registers application dependencies by their abstract interface."""

    def __init__(self) -> None:
        self._dependencies: dict[type[Any], Any] = {}

    def register(self, interface: type[DependencyT], dependency: DependencyT) -> None:
        """Register a dependency implementation for an interface."""
        self._dependencies[interface] = dependency

    def resolve(self, interface: type[DependencyT]) -> DependencyT:
        """Resolve the implementation registered for an interface."""
        try:
            dependency = self._dependencies[interface]
        except KeyError as error:
            raise LookupError(f"No dependency registered for {interface.__name__}.") from error
        return cast(DependencyT, dependency)


def create_container(storage_root: Optional[str] = None) -> DependencyContainer:
    """Build the local deployment's dependency graph at the composition root."""
    root = Path(storage_root or os.getenv("LOCAL_STORAGE_ROOT", ".local-storage"))
    container = DependencyContainer()
    container.register(StorageInterface, LocalStorageProvider(root))
    container.register(QueueInterface, LocalQueueProvider[object]())
    container.register(AuthProvider, LocalAuthProvider())
    return container
