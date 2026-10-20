"""Public Smart Bio Link routes and click tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.db.models import (
    Diagnosis,
    Plant,
    PlantIdentification,
    User,
)
from src.db.models.booking import (
    Booking,
    BookingStatus,
    BookingTimeSlot,
)
from src.db.models.smart_bio_click import SmartBioClick
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)
from src.db.session import get_db_session


router = APIRouter()


SMART_BIO_TARGETS: dict[str, str] = {
    "telegram": "https://t.me/GreenVita_AI_Bot",
    "instagram": "https://www.instagram.com/greenvita_clinic",
    "whatsapp": "https://wa.me/989128111058",
    "bale": "https://ble.ir/greenvita",
}

    
@router.get("/contactus/")
async def smart_bio_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="src/admin/templates")

    tehran = ZoneInfo("Asia/Tehran")
    now = datetime.now(tehran)

    day_start = datetime.combine(
        now.date(),
        datetime.min.time(),
        tzinfo=tehran,
    )
    day_end = day_start + timedelta(days=1)
    week_start = day_start - timedelta(days=6)

    # ------------------------------------------------------
    # Core totals
    # ------------------------------------------------------
    total_users = await session.scalar(
        select(func.count()).select_from(User)
    ) or 0

    total_plants = await session.scalar(
        select(func.count()).select_from(Plant)
    ) or 0

    total_diagnoses = await session.scalar(
        select(func.count()).select_from(Diagnosis)
    ) or 0

    total_identifications = await session.scalar(
        select(func.count()).select_from(PlantIdentification)
    ) or 0

    total_visits = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(Diagnosis.expert_visit_requested.is_(True))
    ) or 0

    # ------------------------------------------------------
    # Visit / schedule metrics
    # ------------------------------------------------------
    pending_visits = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status.in_(["pending", "reviewing"]),
        )
    ) or 0

    scheduled_visits = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status.in_(
                ["scheduled", "confirmed", "in_progress"]
            ),
        )
    ) or 0

    active_booking_statuses = (
        BookingStatus.PENDING,
        BookingStatus.REVIEWING,
        BookingStatus.SCHEDULED,
        BookingStatus.CONFIRMED,
        BookingStatus.IN_PROGRESS,
    )

    active_appointment_statuses = (
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.IN_PROGRESS,
    )

    today_bookings = await session.scalar(
        select(func.count())
        .select_from(Booking)
        .join(
            BookingTimeSlot,
            Booking.time_slot_id == BookingTimeSlot.id,
        )
        .where(
            BookingTimeSlot.starts_at >= day_start,
            BookingTimeSlot.starts_at < day_end,
            Booking.status.in_(active_booking_statuses),
        )
    ) or 0

    today_appointments = await session.scalar(
        select(func.count())
        .select_from(VisitAppointment)
        .where(
            VisitAppointment.start_at >= day_start,
            VisitAppointment.start_at < day_end,
            VisitAppointment.status.in_(active_appointment_statuses),
        )
    ) or 0

    # ------------------------------------------------------
    # Smart Bio metrics
    # ------------------------------------------------------
    smart_bio_total = await session.scalar(
        select(func.count()).select_from(SmartBioClick)
    ) or 0

    now_utc = datetime.now(timezone.utc)
    day_ago = now_utc - timedelta(days=1)
    week_ago = now_utc - timedelta(days=7)

    smart_bio_24h = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= day_ago)
    ) or 0

    smart_bio_7d = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= week_ago)
    ) or 0

    smart_bio_channel_rows = (
        await session.execute(
            select(
                SmartBioClick.channel,
                func.count().label("count"),
            )
            .group_by(SmartBioClick.channel)
            .order_by(func.count().desc())
        )
    ).all()

    smart_bio_channels = {
        row.channel: row.count
        for row in smart_bio_channel_rows
    }

    channel_total = sum(smart_bio_channels.values())

    smart_bio_channel_stats = []
    for channel, count in smart_bio_channels.items():
        percentage = (
            round((count / channel_total) * 100, 1)
            if channel_total
            else 0
        )

        smart_bio_channel_stats.append(
            {
                "channel": channel,
                "count": count,
                "percentage": percentage,
            }
        )

    smart_bio_top_channel = (
        smart_bio_channel_stats[0]
        if smart_bio_channel_stats
        else None
    )

    smart_bio_recent_rows = (
        await session.execute(
            select(
                SmartBioClick.channel,
                SmartBioClick.source_path,
                SmartBioClick.created_at,
            )
            .order_by(SmartBioClick.created_at.desc())
            .limit(15)
        )
    ).all()

    return templates.TemplateResponse(
        "smart_bio.html",
        {
            "request": request,
            "analytics": {
                "generated_at": now.isoformat(),
                "totals": {
                    "users": total_users,
                    "plants": total_plants,
                    "diagnoses": total_diagnoses,
                    "identifications": total_identifications,
                    "visits": total_visits,
                },
                "visits": {
                    "pending": pending_visits,
                    "scheduled": scheduled_visits,
                },
                "today": {
                    "bookings": today_bookings,
                    "appointments": today_appointments,
                    "total": today_bookings + today_appointments,
                },
            },
            "smart_bio": {
                "total": smart_bio_total,
                "channels": smart_bio_channels,
                "channel_stats": smart_bio_channel_stats,
                "top_channel": smart_bio_top_channel,
                "recent": smart_bio_recent_rows,
                "last_24h": smart_bio_24h,
                "last_7d": smart_bio_7d,
            },
        },
    )


@router.get("/go/{channel}")
async def smart_bio_redirect(
    channel: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    target = SMART_BIO_TARGETS.get(channel)

    if target is None:
        return RedirectResponse("/contactus/", status_code=302)

    click = SmartBioClick(
        channel=channel,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        source_path=request.url.path,
    )

    session.add(click)
    await session.commit()

    return RedirectResponse(target, status_code=302)
