from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VisitAppointment(Base, TimestampMixin):
    __tablename__ = "visit_appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    blocked_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    buffer_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=120,
    )

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
    )

    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # رزروهای خارج از درخواست بات
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="bot",
        server_default="bot",
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    customer_phone: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    customer_plant: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    diagnosis = relationship("Diagnosis", back_populates="appointment")

    __table_args__ = (
        Index("ix_visit_appointments_start_at", "start_at"),
        Index("ix_visit_appointments_blocked_until", "blocked_until"),
        Index("ix_visit_appointments_status_start", "status", "start_at"),
    )
