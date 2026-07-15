"""File storage provider port."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


class StorageInterface(ABC):
    """Persists opaque file content behind an implementation-neutral boundary."""

    @abstractmethod
    def save_file(self, path: PathLike, data: bytes) -> None:
        """Persist ``data`` at ``path``."""

    @abstractmethod
    def load_file(self, path: PathLike) -> bytes:
        """Load the bytes persisted at ``path``."""

    @abstractmethod
    def delete_file(self, path: PathLike) -> None:
        """Delete the file at ``path``."""

    @abstractmethod
    def exists(self, path: PathLike) -> bool:
        """Return whether a file exists at ``path``."""

    @abstractmethod
    def list_files(self, directory: PathLike = ".") -> list[str]:
        """Return sorted storage-root-relative file paths under ``directory``."""
