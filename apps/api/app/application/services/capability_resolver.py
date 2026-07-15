"""Runtime capability selection for future processing workloads."""

from typing import Optional

from app.application.services.hardware_detector import HardwareDetector
from app.domain.entities.runtime import (
    GpuPreference,
    ProcessingMode,
    ProcessingProfile,
    RuntimeCapabilities,
)
from app.domain.interfaces.config import ConfigProvider

GIBIBYTE = 1024**3


class CapabilityResolver:
    """Resolve a safe processing profile from configuration and observed hardware."""

    def __init__(
        self, config_provider: ConfigProvider, hardware_detector: HardwareDetector
    ) -> None:
        self._config_provider = config_provider
        self._hardware_detector = hardware_detector

    def resolve(self) -> RuntimeCapabilities:
        """Select CPU or GPU mode without failing when a requested GPU is unavailable."""
        config = self._config_provider.get_config()
        hardware = self._hardware_detector.detect()
        accelerator = self._select_accelerator(
            config.gpu_preference, hardware.cuda_available, hardware.mps_available
        )
        mode = ProcessingMode.GPU if accelerator is not None else ProcessingMode.CPU
        profile = self._select_profile(mode, hardware.available_memory_bytes, hardware.cpu_cores)
        return RuntimeCapabilities(mode=mode, profile=profile, accelerator=accelerator)

    @staticmethod
    def _select_accelerator(
        preference: GpuPreference, cuda_available: bool, mps_available: bool
    ) -> Optional[str]:
        if preference is GpuPreference.CPU:
            return None
        if preference is GpuPreference.CUDA:
            return "cuda" if cuda_available else None
        if preference is GpuPreference.MPS:
            return "mps" if mps_available else None
        if cuda_available:
            return "cuda"
        if mps_available:
            return "mps"
        return None

    @staticmethod
    def _select_profile(
        mode: ProcessingMode, available_memory_bytes: int, cpu_cores: int
    ) -> ProcessingProfile:
        if mode is ProcessingMode.GPU and available_memory_bytes >= 16 * GIBIBYTE:
            return ProcessingProfile.HIGH_PERFORMANCE
        if mode is ProcessingMode.GPU or (
            available_memory_bytes >= 8 * GIBIBYTE and cpu_cores >= 4
        ):
            return ProcessingProfile.BALANCED
        return ProcessingProfile.COMPATIBILITY
