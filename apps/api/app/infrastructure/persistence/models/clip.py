"""Clip persistence model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.video import Video


class Clip(Base):
    """A candidate highlight segment belonging to a source video."""

    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    viral_score: Mapped[float] = mapped_column(Float, nullable=False)
    export_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    video: Mapped["Video"] = relationship(back_populates="clips")
