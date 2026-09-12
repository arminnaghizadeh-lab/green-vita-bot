from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.booking import (
    Booking,
    BookingSlotAssignment,
    BookingStatus,
    BookingTimeSlot,
)
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)

ACTIVE_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.REVIEWING,
    BookingStatus.SCHEDULED,
    BookingStatus.CONFIRMED,
    BookingStatus.IN_PROGRESS,
)

ACTIVE_VISIT_STATUSES = (
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.IN_PROGRESS,
)


async def get_visit_occupied_slot_starts(
    session: AsyncSession,
    start_at: datetime,
    end_at: datetime,
) -> set[datetime]:
    """
    تمام Slotهای Booking که با بازه اشغال‌شده توسط
    VisitAppointment تداخل دارند.

    این تابع overlap واقعی بازه را بررسی می‌کند و فقط
    starts_at را به‌عنوان خروجی برمی‌گرداند.
    """

    result = await session.execute(
        select(BookingTimeSlot.starts_at)
        .join(
            VisitAppointment,
            and_(
                VisitAppointment.start_at < BookingTimeSlot.ends_at,
                VisitAppointment.blocked_until > BookingTimeSlot.starts_at,
                VisitAppointment.status.in_(ACTIVE_VISIT_STATUSES),
            ),
        )
        .where(
            BookingTimeSlot.starts_at < end_at,
            BookingTimeSlot.ends_at > start_at,
        )
    )

    return set(result.scalars().all())


async def find_booking_conflict(
    session: AsyncSession,
    start_at: datetime,
    blocked_until: datetime,
    exclude_booking_id: int | None = None,
) -> tuple[int, datetime, datetime] | None:
    """
    یک Booking فعال که بازه RESERVED + BUFFER آن با
    بازه درخواستی تداخل دارد پیدا می‌کند.
    """

    assignment_window = (
        select(
            BookingSlotAssignment.booking_id.label("booking_id"),
            func.min(
                BookingTimeSlot.starts_at
            ).label("occupied_start"),
            func.max(
                BookingTimeSlot.ends_at
            ).label("occupied_end"),
        )
        .join(
            BookingTimeSlot,
            BookingTimeSlot.id
            == BookingSlotAssignment.time_slot_id,
        )
        .group_by(BookingSlotAssignment.booking_id)
        .subquery()
    )

    stmt = (
        select(
            Booking.id,
            assignment_window.c.occupied_start,
            assignment_window.c.occupied_end,
        )
        .join(
            assignment_window,
            assignment_window.c.booking_id == Booking.id,
        )
        .where(
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            assignment_window.c.occupied_start < blocked_until,
            assignment_window.c.occupied_end > start_at,
        )
        .order_by(
            assignment_window.c.occupied_start,
            Booking.id,
        )
        .limit(1)
    )

    if exclude_booking_id is not None:
        stmt = stmt.where(
            Booking.id != exclude_booking_id
        )

    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        return None

    booking_id, occupied_start, occupied_end = row

    return booking_id, occupied_start, occupied_end
