"""Conversation model — تاریخچه‌ی پیام‌های رد و بدل شده با دستیار هوشمند."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.plant import Plant
    from src.db.models.user import User


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_id: Mapped[int | None] = mapped_column(
        ForeignKey("plants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # نام پروایدر هوش مصنوعی که پاسخ را تولید کرده (claude/gemini/openai) — برای اشکال‌زدایی و آمار
    ai_provider: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="conversations")
    plant: Mapped["Plant | None"] = relationship(back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id} role={self.role}>"
