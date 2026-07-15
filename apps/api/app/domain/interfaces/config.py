"""Configuration provider port."""

from abc import ABC, abstractmethod

from app.domain.entities.runtime import AppConfig


class ConfigProvider(ABC):
    """Exposes validated application configuration to application services."""

    @abstractmethod
    def get_config(self) -> AppConfig:
        """Return the validated immutable configuration."""
