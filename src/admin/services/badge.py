"""Central admin PWA badge counter."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Diagnosis
from src.db.models.booking import Booking, BookingStatus


async def get_admin_badge_count(
    session: AsyncSession,
) -> int:
    """Return the number of actionable items for the admin PWA badge."""

    pending_visits = await session.scalar(
        select(func.count(Diagnosis.id)).where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status == "pending",
        )
    )

    pending_bookings = await session.scalar(
        select(func.count(Booking.id)).where(
            Booking.status == BookingStatus.PENDING,
        )
    )

    return int(pending_visits or 0) + int(pending_bookings or 0)
