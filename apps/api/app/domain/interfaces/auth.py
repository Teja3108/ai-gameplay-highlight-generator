"""Authentication provider port."""

from abc import ABC, abstractmethod

from app.domain.entities.user import User


class AuthProvider(ABC):
    """Provides the identity associated with the current application context."""

    @abstractmethod
    def get_current_user(self) -> User:
        """Return the current authenticated user."""
