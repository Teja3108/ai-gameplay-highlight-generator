"""Settings persistence model."""

from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Settings(Base):
    """Application-level processing preferences."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    output_directory: Mapped[str] = mapped_column(String(1024), nullable=False)
    temp_directory: Mapped[str] = mapped_column(String(1024), nullable=False)
    preferred_gpu: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    smart_crop_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
