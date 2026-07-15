"""Authentication identity entities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """An authenticated application identity independent of any auth vendor."""

    identifier: str
    username: str
