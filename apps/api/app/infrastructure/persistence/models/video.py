"""Video persistence model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.clip import Clip


class Video(Base):
    """A source video registered for future processing."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    clips: Mapped[list["Clip"]] = relationship(back_populates="video", cascade="all, delete-orphan")
