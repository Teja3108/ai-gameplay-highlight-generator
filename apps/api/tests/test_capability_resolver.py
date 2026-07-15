from pathlib import Path

from app.application.services.capability_resolver import CapabilityResolver
from app.domain.entities.runtime import (
    AppConfig,
    GpuPreference,
    HardwareProfile,
    LogLevel,
    ProcessingMode,
    ProcessingProfile,
)


class StaticConfigProvider:
    def __init__(self, config):
        self._config = config

    def get_config(self):
        return self._config


class StaticHardwareDetector:
    def __init__(self, profile):
        self._profile = profile

    def detect(self):
        return self._profile


def make_config(gpu_preference):
    return AppConfig(
        database_url="sqlite:///:memory:",
        storage_root=Path(".local-storage"),
        temp_directory=Path("./data/tmp"),
        log_level=LogLevel.INFO,
        gpu_preference=gpu_preference,
        model_cache_path=Path("./data/models"),
        output_directory=Path("./data/output"),
    )


def make_hardware(cuda_available, mps_available, available_memory_bytes, cpu_cores=8):
    return HardwareProfile(
        cpu_name="CPU",
        cpu_cores=cpu_cores,
        total_memory_bytes=available_memory_bytes,
        available_memory_bytes=available_memory_bytes,
        operating_system="Test",
        python_version="3.9.0",
        cuda_available=cuda_available,
        mps_available=mps_available,
        directml_available=False,
    )


def test_capability_resolver_selects_high_performance_cuda_profile():
    resolver = CapabilityResolver(
        StaticConfigProvider(make_config(GpuPreference.AUTO)),
        StaticHardwareDetector(make_hardware(True, False, 16 * 1024**3)),
    )

    capabilities = resolver.resolve()

    assert capabilities.mode is ProcessingMode.GPU
    assert capabilities.profile is ProcessingProfile.HIGH_PERFORMANCE
    assert capabilities.accelerator == "cuda"


def test_capability_resolver_falls_back_to_cpu_compatibility_mode():
    resolver = CapabilityResolver(
        StaticConfigProvider(make_config(GpuPreference.CUDA)),
        StaticHardwareDetector(make_hardware(False, False, 4 * 1024**3, cpu_cores=2)),
    )

    capabilities = resolver.resolve()

    assert capabilities.mode is ProcessingMode.CPU
    assert capabilities.profile is ProcessingProfile.COMPATIBILITY
    assert capabilities.accelerator is None
