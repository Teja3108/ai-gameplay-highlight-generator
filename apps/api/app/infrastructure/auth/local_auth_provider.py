"""Local authentication adapter for the non-authenticated V1 deployment."""

from typing import Optional

from app.domain.entities.user import User
from app.domain.interfaces.auth import AuthProvider


class LocalAuthProvider(AuthProvider):
    """Return a stable local identity while external authentication is disabled."""

    def __init__(self, user: Optional[User] = None) -> None:
        self._user = user or User(identifier="local-user", username="local")

    def get_current_user(self) -> User:
        """Return the local development identity."""
        return self._user
