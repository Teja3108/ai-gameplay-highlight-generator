"""Filesystem-backed storage adapter."""

import os
import tempfile
from pathlib import Path

from app.domain.interfaces.storage import PathLike, StorageInterface


class LocalStorageProvider(StorageInterface):
    """Store files beneath a configured local root without path traversal."""

    def __init__(self, root_directory: PathLike) -> None:
        self._root_directory = Path(root_directory).resolve()
        self._root_directory.mkdir(parents=True, exist_ok=True)

    def save_file(self, path: PathLike, data: bytes) -> None:
        """Atomically write bytes to a storage-root-relative path."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(dir=target.parent, prefix=".upload-")
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(data)
            os.replace(temporary_path, target)
        except Exception:
            Path(temporary_path).unlink(missing_ok=True)
            raise

    def load_file(self, path: PathLike) -> bytes:
        """Load raw bytes from a storage-root-relative path."""
        return self._resolve_path(path).read_bytes()

    def delete_file(self, path: PathLike) -> None:
        """Delete a storage-root-relative file."""
        self._resolve_path(path).unlink()

    def exists(self, path: PathLike) -> bool:
        """Return whether a storage-root-relative path is a file."""
        return self._resolve_path(path).is_file()

    def list_files(self, directory: PathLike = ".") -> list[str]:
        """Return sorted storage-root-relative files recursively under a directory."""
        resolved_directory = self._resolve_path(directory)
        if not resolved_directory.exists():
            return []
        if not resolved_directory.is_dir():
            raise NotADirectoryError(resolved_directory)

        files = []
        for candidate in resolved_directory.rglob("*"):
            if candidate.is_file() and self._is_within_root(candidate):
                files.append(candidate.relative_to(self._root_directory).as_posix())
        return sorted(files)

    def _resolve_path(self, path: PathLike) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            raise ValueError("Storage paths must be relative to the configured root directory.")

        resolved = (self._root_directory / candidate).resolve()
        if not self._is_within_root(resolved):
            raise ValueError("Storage path escapes the configured root directory.")
        return resolved

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._root_directory)
        except ValueError:
            return False
        return True
