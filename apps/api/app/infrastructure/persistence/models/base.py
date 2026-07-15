"""Declarative base for all SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class shared by all persistence models."""
