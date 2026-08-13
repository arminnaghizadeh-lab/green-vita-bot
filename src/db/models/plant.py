"""Plant model — پرونده‌ی هر گیاهی که کاربر ثبت می‌کند."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.conversation import Conversation
    from src.db.models.diagnosis import Diagnosis
    from src.db.models.reminder import Reminder
    from src.db.models.user import User


class PlantHealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    SICK = "sick"
    UNDER_TREATMENT = "under_treatment"
    RECOVERED = "recovered"
    UNKNOWN = "unknown"


class Plant(Base, TimestampMixin):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    health_status: Mapped[PlantHealthStatus] = mapped_column(
        Enum(PlantHealthStatus), default=PlantHealthStatus.UNKNOWN, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="plants")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="plant", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="plant", cascade="all, delete-orphan"
    )
    diagnoses: Mapped[list["Diagnosis"]] = relationship(
        back_populates="plant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Plant id={self.id} name={self.name!r} owner_id={self.owner_id}>"
