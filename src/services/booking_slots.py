from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import jdatetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.booking import BookingSchedule, BookingTimeSlot

TEHRAN = ZoneInfo("Asia/Tehran")


def jalali_to_gregorian_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    jd = jdatetime.datetime(
        year, month, day, hour, minute, tzinfo=TEHRAN
    )
    return jd.togregorian()


async def generate_slots_for_date(
    session: AsyncSession,
    target_date: datetime,
) -> int:
    target_date = target_date.astimezone(TEHRAN)
    weekday = (target_date.weekday() + 2) % 7

    result = await session.execute(
        select(BookingSchedule).where(
            BookingSchedule.weekday == weekday,
            BookingSchedule.is_active.is_(True),
        )
    )
    schedules = result.scalars().all()

    created = 0

    for schedule in schedules:
        current = datetime.combine(
            target_date.date(),
            schedule.start_time,
            tzinfo=TEHRAN,
        )
        end = datetime.combine(
            target_date.date(),
            schedule.end_time,
            tzinfo=TEHRAN,
        )

        duration = timedelta(minutes=schedule.slot_duration_minutes)

        while current + duration <= end:
            slot_end = current + duration

            exists = await session.scalar(
                select(BookingTimeSlot.id).where(
                    BookingTimeSlot.schedule_id == schedule.id,
                    BookingTimeSlot.starts_at == current,
                )
            )

            if exists is None:
                session.add(
                    BookingTimeSlot(
                        schedule_id=schedule.id,
                        starts_at=current,
                        ends_at=slot_end,
                        is_available=True,
                    )
                )
                created += 1

            current = slot_end

    await session.commit()
    return created


async def generate_slots_for_range(
    session: AsyncSession,
    start_date: datetime,
    days: int = 30,
) -> int:
    total = 0

    for offset in range(days):
        target = start_date + timedelta(days=offset)
        total += await generate_slots_for_date(session, target)

    return total
