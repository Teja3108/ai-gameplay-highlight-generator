"""Best-effort runtime hardware detection."""

import os
import platform
import shutil
from typing import Callable, Optional

import psutil

from app.domain.entities.runtime import HardwareProfile

MemoryProvider = Callable[[], tuple[int, int]]
CommandLocator = Callable[[str], Optional[str]]


class HardwareDetector:
    """Detect local hardware without requiring a GPU or vendor SDK."""

    def __init__(
        self,
        memory_provider: Optional[MemoryProvider] = None,
        command_locator: Optional[CommandLocator] = None,
        cpu_count_provider: Optional[Callable[[], Optional[int]]] = None,
        system_provider: Optional[Callable[[], str]] = None,
        machine_provider: Optional[Callable[[], str]] = None,
        processor_provider: Optional[Callable[[], str]] = None,
        python_version_provider: Optional[Callable[[], str]] = None,
    ) -> None:
        self._memory_provider = memory_provider or self._get_memory
        self._command_locator = command_locator or shutil.which
        self._cpu_count_provider = cpu_count_provider or os.cpu_count
        self._system_provider = system_provider or platform.system
        self._machine_provider = machine_provider or platform.machine
        self._processor_provider = processor_provider or platform.processor
        self._python_version_provider = python_version_provider or platform.python_version

    def detect(self) -> HardwareProfile:
        """Return a profile even when accelerator information is unavailable."""
        operating_system = self._system_provider()
        machine = self._machine_provider().lower()
        cpu_name = self._processor_provider() or machine or "unknown"
        total_memory, available_memory = self._memory_provider()
        cuda_available = self._command_locator("nvidia-smi") is not None
        mps_available = operating_system == "Darwin" and machine in {"arm64", "aarch64"}

        return HardwareProfile(
            cpu_name=cpu_name,
            cpu_cores=self._cpu_count_provider() or 1,
            total_memory_bytes=total_memory,
            available_memory_bytes=available_memory,
            operating_system=operating_system,
            python_version=self._python_version_provider(),
            cuda_available=cuda_available,
            mps_available=mps_available,
            directml_available=False,
        )

    @staticmethod
    def _get_memory() -> tuple[int, int]:
        memory = psutil.virtual_memory()
        return memory.total, memory.available
