"""Application composition root and dependency registry."""

from pathlib import Path
from typing import Any, Optional, TypeVar, cast

from app.application.services.capability_resolver import CapabilityResolver
from app.application.services.hardware_detector import HardwareDetector
from app.domain.interfaces.auth import AuthProvider
from app.domain.interfaces.config import ConfigProvider
from app.domain.interfaces.queue import QueueInterface
from app.domain.interfaces.repositories import (
    ClipRepositoryInterface,
    JobRepositoryInterface,
    SettingsRepositoryInterface,
    VideoRepositoryInterface,
)
from app.domain.interfaces.storage import StorageInterface
from app.infrastructure.auth.local_auth_provider import LocalAuthProvider
from app.infrastructure.config.environment_config_provider import (
    EnvironmentConfigProvider,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.repositories.clip_repository import ClipRepository
from app.infrastructure.persistence.repositories.job_repository import JobRepository
from app.infrastructure.persistence.repositories.settings_repository import (
    SettingsRepository,
)
from app.infrastructure.persistence.repositories.video_repository import VideoRepository
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


def create_container(
    storage_root: Optional[str] = None, database_url: Optional[str] = None
) -> DependencyContainer:
    """Build the local deployment's dependency graph at the composition root."""
    container = DependencyContainer()
    config_provider = EnvironmentConfigProvider()
    config = config_provider.get_config()
    root = Path(storage_root) if storage_root else config.storage_root
    hardware_detector = HardwareDetector()

    container.register(ConfigProvider, config_provider)
    container.register(HardwareDetector, hardware_detector)
    container.register(CapabilityResolver, CapabilityResolver(config_provider, hardware_detector))
    container.register(StorageInterface, LocalStorageProvider(root))
    container.register(QueueInterface, LocalQueueProvider[object]())
    container.register(AuthProvider, LocalAuthProvider())
    engine = create_database_engine(database_url or config.database_url)
    session_factory = create_session_factory(engine)
    container.register(VideoRepositoryInterface, VideoRepository(session_factory))
    container.register(ClipRepositoryInterface, ClipRepository(session_factory))
    container.register(JobRepositoryInterface, JobRepository(session_factory))
    container.register(SettingsRepositoryInterface, SettingsRepository(session_factory))
    return container
