"""Reminder model — یادآوری‌های زمان‌بندی‌شده برای هر گیاه.

توجه: منطق اجرای زمان‌بندی (Scheduler) در فاز بعدی پیاده‌سازی می‌شود.
اینجا فقط ساختار داده تعریف شده تا مایگریشن اولیه کامل باشد.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.plant import Plant
    from src.db.models.user import User


class ReminderType(str, enum.Enum):
    WATERING = "watering"
    FERTILIZING = "fertilizing"
    OTHER = "other"


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)

    reminder_type: Mapped[ReminderType] = mapped_column(Enum(ReminderType), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="reminders")
    plant: Mapped["Plant"] = relationship(back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} type={self.reminder_type} plant_id={self.plant_id}>"
