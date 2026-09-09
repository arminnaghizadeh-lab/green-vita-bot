from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.services.badge import get_admin_badge_count
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import (
    Diagnosis,
    Plant,
    PlantIdentification,
    User,
    SmartBioClick,
)
from src.db.models.booking import (
    Booking,
    BookingStatus,
    BookingTimeSlot,
)
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/api/badge-count", include_in_schema=False)
async def admin_badge_count(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    count = await get_admin_badge_count(session)

    return {
        "count": count,
    }


@router.get("/api/reservations/overview", include_in_schema=False)
async def reservations_overview(
    request: Request,
    start_date: str | None = None,
    days: int = 7,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    if days < 1 or days > 31:
        days = 7

    tehran = ZoneInfo("Asia/Tehran")
    today = datetime.now(tehran).date()

    if start_date:
        try:
            start_day = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            start_day = today
    else:
        start_day = today

    end_day = start_day + timedelta(days=days)

    start_dt = datetime.combine(
        start_day,
        datetime.min.time(),
        tzinfo=tehran,
    )
    end_dt = datetime.combine(
        end_day,
        datetime.min.time(),
        tzinfo=tehran,
    )

    active_booking_statuses = (
        BookingStatus.PENDING,
        BookingStatus.CONFIRMED,
    )

    active_appointment_statuses = (
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.IN_PROGRESS,
    )

    booking_rows = (
        await session.execute(
            select(Booking, BookingTimeSlot)
            .join(
                BookingTimeSlot,
                Booking.time_slot_id == BookingTimeSlot.id,
            )
            .where(
                Booking.status.in_(active_booking_statuses),
                BookingTimeSlot.starts_at < end_dt,
                BookingTimeSlot.ends_at > start_dt,
            )
            .order_by(BookingTimeSlot.starts_at)
        )
    ).all()

    appointment_rows = (
        await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.status.in_(active_appointment_statuses),
                VisitAppointment.start_at < end_dt,
                VisitAppointment.blocked_until > start_dt,
            )
            .order_by(VisitAppointment.start_at)
        )
    ).scalars().all()

    slot_rows = (
        await session.execute(
            select(BookingTimeSlot)
            .where(
                BookingTimeSlot.starts_at >= start_dt,
                BookingTimeSlot.starts_at < end_dt,
            )
            .order_by(BookingTimeSlot.starts_at)
        )
    ).scalars().all()

    events_by_day = {
        (start_day + timedelta(days=i)).isoformat(): []
        for i in range(days)
    }

    slots_by_day = {
        (start_day + timedelta(days=i)).isoformat(): []
        for i in range(days)
    }

    source_labels = {
        "online": {
            "key": "website",
            "label": "🌐 سایت",
        },
        "admin": {
            "key": "phone",
            "label": "☎️ تلفنی",
        },
        "bot": {
            "key": "telegram",
            "label": "🤖 بات تلگرام",
        },
        "manual": {
            "key": "phone",
            "label": "☎️ تلفنی",
        },
    }

    for booking, slot in booking_rows:
        local_start = slot.starts_at.astimezone(tehran)
        key = local_start.date().isoformat()

        if key not in events_by_day:
            continue

        raw_source = (
            booking.source.value
            if hasattr(booking.source, "value")
            else str(booking.source)
        )

        source = source_labels.get(
            raw_source,
            {
                "key": raw_source,
                "label": raw_source,
            },
        )

        status = (
            booking.status.value
            if hasattr(booking.status, "value")
            else str(booking.status)
        )

        events_by_day[key].append(
            {
                "type": "booking",
                "id": booking.id,
                "slot_id": slot.id,
                "start_at": slot.starts_at.isoformat(),
                "end_at": slot.ends_at.isoformat(),
                "name": booking.customer_name or "بدون نام",
                "phone": booking.customer_phone,
                "source": source["key"],
                "source_label": source["label"],
                "status": status,
                "tracking_code": getattr(
                    booking,
                    "tracking_code",
                    None,
                ),
                "service_id": getattr(
                    booking,
                    "service_id",
                    None,
                ),
            }
        )

    for appointment in appointment_rows:
        local_start = appointment.start_at.astimezone(tehran)
        key = local_start.date().isoformat()

        if key not in events_by_day:
            continue

        raw_source = appointment.source or "bot"

        source = source_labels.get(
            raw_source,
            {
                "key": raw_source,
                "label": raw_source,
            },
        )

        status = (
            appointment.status.value
            if hasattr(appointment.status, "value")
            else str(appointment.status)
        )

        events_by_day[key].append(
            {
                "type": "visit",
                "id": appointment.id,
                "slot_id": None,
                "start_at": appointment.start_at.isoformat(),
                "end_at": appointment.end_at.isoformat(),
                "name": appointment.customer_name or "ویزیت درخواستی",
                "phone": appointment.customer_phone,
                "plant": appointment.customer_plant,
                "source": source["key"],
                "source_label": source["label"],
                "status": status,
                "tracking_code": None,
                "service_id": None,
                "diagnosis_id": appointment.diagnosis_id,
            }
        )

    for slot in slot_rows:
        local_start = slot.starts_at.astimezone(tehran)
        key = local_start.date().isoformat()

        if key not in slots_by_day:
            continue

        slots_by_day[key].append(
            {
                "id": slot.id,
                "start_at": slot.starts_at.isoformat(),
                "end_at": slot.ends_at.isoformat(),
                "enabled": bool(slot.is_enabled),
                "available": bool(slot.is_available),
            }
        )

    for items in events_by_day.values():
        items.sort(key=lambda item: item["start_at"])

    days_output = []

    fa_weekdays = [
        "دوشنبه",
        "سه‌شنبه",
        "چهارشنبه",
        "پنجشنبه",
        "جمعه",
        "شنبه",
        "یکشنبه",
    ]

    for i in range(days):
        current = start_day + timedelta(days=i)
        key = current.isoformat()
        days_output.append(
            {
                "date": key,
                "weekday": fa_weekdays[current.weekday()],
                "events": events_by_day[key],
                "slots": slots_by_day[key],
                "count": len(events_by_day[key]),
                "is_today": current == today,
            }
        )

    pending_requests = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_scheduled_at.is_(None),
        )
    )

    return {
        "start_date": start_day.isoformat(),
        "end_date": (end_day - timedelta(days=1)).isoformat(),
        "today": today.isoformat(),
        "pending_requests": pending_requests or 0,
        "days": days_output,
    }



@router.get("/api/overview", include_in_schema=False)
async def admin_overview(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    tehran = ZoneInfo("Asia/Tehran")
    now = datetime.now(tehran)

    day_start = datetime.combine(
        now.date(),
        datetime.min.time(),
        tzinfo=tehran,
    )
    day_end = day_start + timedelta(days=1)

    week_start = day_start - timedelta(days=6)

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

    pending_visits = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status.in_(
                [
                    "pending",
                    "reviewing",
                ]
            ),
        )
    ) or 0

    scheduled_visits = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status.in_(
                [
                    "scheduled",
                    "confirmed",
                    "in_progress",
                ]
            ),
        )
    ) or 0

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
            Booking.status.in_(
                [
                    BookingStatus.PENDING,
                    BookingStatus.CONFIRMED,
                ]
            ),
        )
    ) or 0

    today_appointments = await session.scalar(
        select(func.count())
        .select_from(VisitAppointment)
        .where(
            VisitAppointment.start_at >= day_start,
            VisitAppointment.start_at < day_end,
            VisitAppointment.status.in_(
                [
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                ]
            ),
        )
    ) or 0

    smart_bio_7d = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= week_start)
    ) or 0

    return {
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
        "smart_bio": {
            "last_7d": smart_bio_7d,
        },
    }


@router.get("/")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    users_count = await session.scalar(select(func.count()).select_from(User))
    plants_count = await session.scalar(select(func.count()).select_from(Plant))
    diagnoses_count = await session.scalar(select(func.count()).select_from(Diagnosis))
    identifications_count = await session.scalar(
        select(func.count()).select_from(PlantIdentification)
    )
    visits_count = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(Diagnosis.expert_visit_requested.is_(True))
    )

    smart_bio_total = await session.scalar(
        select(func.count()).select_from(SmartBioClick)
    )

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

    smart_bio_channel_total = sum(smart_bio_channels.values())

    smart_bio_channel_stats = []
    for channel, count in smart_bio_channels.items():
        percentage = (
            round((count / smart_bio_channel_total) * 100, 1)
            if smart_bio_channel_total
            else 0
        )

        smart_bio_channel_stats.append(
            {
                "channel": channel,
                "count": count,
                "percentage": percentage,
            }
        )

    smart_bio_channel_stats.sort(
        key=lambda item: item["count"],
        reverse=True,
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
            .limit(10)
        )
    ).all()


    now_utc = datetime.now(timezone.utc)
    day_ago = now_utc - timedelta(days=1)
    week_ago = now_utc - timedelta(days=7)

    smart_bio_24h = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= day_ago)
    )

    smart_bio_7d = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= week_ago)
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "stats": {
                "users": users_count or 0,
                "plants": plants_count or 0,
                "diagnoses": diagnoses_count or 0,
                "identifications": identifications_count or 0,
                "visits": visits_count or 0,
            },
            "smart_bio": {
                "total": smart_bio_total or 0,
                "channels": smart_bio_channels,
                "channel_stats": smart_bio_channel_stats,
                "top_channel": smart_bio_top_channel,
                "recent": smart_bio_recent_rows,
                "last_24h": smart_bio_24h or 0,
                "last_7d": smart_bio_7d or 0,
            },
        },
    )
