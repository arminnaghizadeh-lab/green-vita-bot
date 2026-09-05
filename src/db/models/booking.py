from __future__ import annotations

import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class BookingSource(str, enum.Enum):
    ONLINE = "online"
    ADMIN = "admin"
    BOT = "bot"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Service(Base, TimestampMixin):
    __tablename__ = "booking_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 0), nullable=False, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    schedules: Mapped[list["BookingSchedule"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_booking_services_id", "id"),
    )


class BookingSchedule(Base, TimestampMixin):
    __tablename__ = "booking_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("booking_services.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    service: Mapped["Service"] = relationship(back_populates="schedules")
    slots: Mapped[list["BookingTimeSlot"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_booking_schedules_id", "id"),
        Index("ix_booking_schedules_weekday", "weekday"),
    )


class BookingTimeSlot(Base, TimestampMixin):
    __tablename__ = "booking_time_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("booking_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    schedule: Mapped["BookingSchedule"] = relationship(back_populates="slots")
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="time_slot",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "starts_at",
            name="booking_time_slots_schedule_id_starts_at_key",
        ),
        Index("ix_booking_time_slots_id", "id"),
        Index("ix_booking_time_slots_starts_at", "starts_at"),
    )


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("booking_services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    time_slot_id: Mapped[int] = mapped_column(
        ForeignKey("booking_time_slots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped[BookingSource] = mapped_column(
        Enum(BookingSource),
        nullable=False,
        default=BookingSource.ONLINE,
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus),
        nullable=False,
        default=BookingStatus.PENDING,
    )

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    plant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plant_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    base_amount: Mapped[float] = mapped_column(Numeric(12, 0), nullable=False)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 0),
        nullable=False,
        default=0,
    )
    final_amount: Mapped[float] = mapped_column(Numeric(12, 0), nullable=False)

    time_slot: Mapped["BookingTimeSlot"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship()
    user = relationship("User")

    __table_args__ = (
        Index("ix_bookings_id", "id"),
        Index("ix_bookings_status_time_slot_id", "status", "time_slot_id"),
        Index("ix_bookings_customer_phone", "customer_phone"),
    )
