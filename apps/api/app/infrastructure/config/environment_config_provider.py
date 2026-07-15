"""Typed configuration loaded from defaults, .env files, and environment variables."""

import os
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Optional, TypeVar

from dotenv import dotenv_values

from app.domain.entities.runtime import AppConfig, GpuPreference, LogLevel
from app.domain.interfaces.config import ConfigProvider

DEFAULT_DATABASE_URL = "sqlite:///./data/gameplay.db"
EnumT = TypeVar("EnumT", bound=Enum)


class EnvironmentConfigProvider(ConfigProvider):
    """Load an immutable configuration with environment variables taking precedence."""

    def __init__(
        self,
        environment: Optional[Mapping[str, str]] = None,
        dotenv_path: Optional[Path] = None,
    ) -> None:
        self._environment = environment
        self._dotenv_path = dotenv_path or Path(".env")
        self._config = self._load_config()

    def get_config(self) -> AppConfig:
        """Return the validated configuration."""
        return self._config

    def _load_config(self) -> AppConfig:
        dotenv_values_map = {
            key: value
            for key, value in dotenv_values(self._dotenv_path).items()
            if value is not None
        }
        environment = dict(self._environment) if self._environment is not None else dict(os.environ)
        values = {**dotenv_values_map, **environment}

        database_url = values.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        if not database_url or "://" not in database_url:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy database URL.")

        return AppConfig(
            database_url=database_url,
            storage_root=self._path_value(values, "STORAGE_ROOT", ".local-storage"),
            temp_directory=self._path_value(values, "TEMP_DIRECTORY", "./data/tmp"),
            log_level=self._enum_value(values, "LOG_LEVEL", LogLevel, LogLevel.INFO),
            gpu_preference=self._enum_value(
                values, "GPU_PREFERENCE", GpuPreference, GpuPreference.AUTO
            ),
            model_cache_path=self._path_value(values, "MODEL_CACHE_PATH", "./data/models"),
            output_directory=self._path_value(values, "OUTPUT_DIRECTORY", "./data/output"),
        )

    @staticmethod
    def _path_value(values: Mapping[str, str], key: str, default: str) -> Path:
        value = values.get(key, default).strip()
        if not value:
            raise ValueError(f"{key} must not be empty.")
        return Path(value)

    @staticmethod
    def _enum_value(
        values: Mapping[str, str], key: str, enum_type: type[EnumT], default: EnumT
    ) -> EnumT:
        value = values.get(key, default.value).strip()
        try:
            return enum_type(value.upper() if enum_type is LogLevel else value.lower())
        except ValueError as error:
            allowed = ", ".join(member.value for member in enum_type)
            raise ValueError(f"{key} must be one of: {allowed}.") from error
