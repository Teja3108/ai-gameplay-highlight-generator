"""Configuration and hardware capability entities."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class LogLevel(str, Enum):
    """Supported application log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class GpuPreference(str, Enum):
    """Requested hardware accelerator preference."""

    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


class ProcessingMode(str, Enum):
    """Compute mode selected for runtime processing."""

    CPU = "cpu"
    GPU = "gpu"


class ProcessingProfile(str, Enum):
    """Coarse processing profile used by future workloads."""

    HIGH_PERFORMANCE = "high_performance"
    BALANCED = "balanced"
    COMPATIBILITY = "compatibility"


@dataclass(frozen=True)
class AppConfig:
    """Validated, immutable application configuration."""

    database_url: str
    storage_root: Path
    temp_directory: Path
    log_level: LogLevel
    gpu_preference: GpuPreference
    model_cache_path: Path
    output_directory: Path


@dataclass(frozen=True)
class HardwareProfile:
    """Hardware and accelerator capabilities observed at runtime."""

    cpu_name: str
    cpu_cores: int
    total_memory_bytes: int
    available_memory_bytes: int
    operating_system: str
    python_version: str
    cuda_available: bool
    mps_available: bool
    directml_available: bool


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Resolved compute mode and workload profile."""

    mode: ProcessingMode
    profile: ProcessingProfile
    accelerator: Optional[str]
