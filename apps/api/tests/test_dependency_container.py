import pytest
from app.core.container import DependencyContainer, create_container
from app.domain.interfaces.auth import AuthProvider
from app.domain.interfaces.queue import QueueInterface
from app.domain.interfaces.storage import StorageInterface


def test_local_container_registers_dependencies_by_interface(tmp_path):
    container = create_container(str(tmp_path))

    assert isinstance(container.resolve(StorageInterface), StorageInterface)
    assert isinstance(container.resolve(QueueInterface), QueueInterface)
    assert isinstance(container.resolve(AuthProvider), AuthProvider)


def test_container_raises_for_unregistered_interface():
    class UnregisteredInterface:
        pass

    with pytest.raises(LookupError):
        DependencyContainer().resolve(UnregisteredInterface)
