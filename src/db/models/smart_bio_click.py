"""Smart Bio Link click tracking model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class SmartBioClick(Base, TimestampMixin):
    __tablename__ = "smart_bio_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    referer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SmartBioClick id={self.id} "
            f"channel={self.channel!r}>"
        )
