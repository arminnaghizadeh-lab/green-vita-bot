"""Web Push subscription model for admin PWA notifications."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class PushSubscription(Base, TimestampMixin):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)

    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    p256dh: Mapped[str] = mapped_column(String(512), nullable=False)
    auth: Mapped[str] = mapped_column(String(512), nullable=False)

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<PushSubscription id={self.id} active={self.is_active}>"
