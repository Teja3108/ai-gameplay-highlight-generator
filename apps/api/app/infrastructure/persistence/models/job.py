"""Job persistence model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Job(Base):
    """A durable record of work to be processed by a future application layer."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_stage: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
