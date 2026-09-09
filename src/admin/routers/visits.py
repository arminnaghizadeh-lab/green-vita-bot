from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.services.push import send_push
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.session import AsyncSessionLocal
from src.db.models import Diagnosis, Plant, User
from src.db.models.plant_identification import PlantIdentification
from src.db.models.booking import Booking, BookingStatus, Service
from src.db.models.booking import BookingTimeSlot
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)
from src.db.models.visit_status import VisitStatus
from src.services.appointment_availability import (
    find_booking_conflict,
)
from src.services.visit_scheduler import (
    AppointmentConflict,
    AppointmentNotFound,
    InvalidAppointmentTime,
    SchedulerError,
    cancel_appointment,
    create_appointment,
    is_slot_available,
    reschedule_appointment,
)

router = APIRouter(tags=["visits"])
templates = Jinja2Templates(directory="src/admin/templates")

STATUS_LABELS = {
    VisitStatus.PENDING.value: "در انتظار بررسی",
    VisitStatus.REVIEWING.value: "در حال بررسی",
    VisitStatus.SCHEDULED.value: "زمان‌بندی‌شده",
    VisitStatus.CONFIRMED.value: "تأییدشده",
    VisitStatus.IN_PROGRESS.value: "در حال انجام",
    VisitStatus.COMPLETED.value: "انجام‌شده",
    VisitStatus.CANCELLED.value: "لغوشده",
}

STATUS_CLASSES = {
    "pending": "status-pending",
    "reviewing": "status-reviewing",
    "scheduled": "status-scheduled",
    "confirmed": "status-confirmed",
    "in_progress": "status-progress",
    "completed": "status-completed",
    "cancelled": "status-cancelled",
}

CALENDAR_ACTIVE_STATUSES = (
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.IN_PROGRESS,
)

DEFAULT_SLOT_STEP_MINUTES = 30


def _format_visit_datetime(value: datetime, fmt: str) -> str:
    settings = get_settings()
    return value.astimezone(ZoneInfo(settings.timezone)).strftime(fmt)


async def _send_visit_push_safe(
    *,
    title: str,
    body: str,
    url: str = "/visits",
    context: dict | None = None,
) -> None:
    """
    Push خطا نباید روی transaction اصلی Visit اثر بگذارد.
    ارسال در یک session جدا و بعد از commit انجام می‌شود.
    """
    try:
        async with AsyncSessionLocal() as push_session:
            await send_push(
                push_session,
                title=title,
                body=body,
                url=url,
            )
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "visit_admin_push_failed",
            extra=context or {},
        )


def _parse_datetime(value: str, field_name: str) -> datetime:
    value = value.strip()

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}",
        ) from exc

    # فرم datetime-local زمان را بدون timezone ارسال می‌کند.
    # زمان پنل ادمین به صورت local در نظر گرفته می‌شود.
    if parsed.tzinfo is None:
        from zoneinfo import ZoneInfo

        settings = get_settings()
        parsed = parsed.replace(tzinfo=ZoneInfo(settings.timezone))

    return parsed.astimezone(timezone.utc)


def _appointment_json(appointment: VisitAppointment) -> dict:
    status = (
        appointment.status.value
        if hasattr(appointment.status, "value")
        else appointment.status
    )

    return {
        "id": appointment.id,
        "diagnosis_id": appointment.diagnosis_id,
        "identification_id": getattr(appointment, "identification_id", None),
        "start_at": appointment.start_at.isoformat(),
        "end_at": appointment.end_at.isoformat(),
        "blocked_until": appointment.blocked_until.isoformat(),
        "duration_minutes": appointment.duration_minutes,
        "buffer_minutes": appointment.buffer_minutes,
        "status": status,
        "admin_note": appointment.admin_note,
    }


@router.get("/api/calendar/events")
async def calendar_events(
    request: Request,
    start_at: str,
    end_at: str,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    start = _parse_datetime(start_at, "start_at")
    end = _parse_datetime(end_at, "end_at")

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="end_at must be after start_at",
        )

    result = await session.execute(
        select(
            VisitAppointment,
            Diagnosis,
            PlantIdentification,
            User,
            Plant,
        )
        .outerjoin(
            Diagnosis,
            VisitAppointment.diagnosis_id == Diagnosis.id,
        )
        .outerjoin(
            PlantIdentification,
            VisitAppointment.identification_id == PlantIdentification.id,
        )
        .outerjoin(
            User,
            or_(
                Diagnosis.user_id == User.id,
                PlantIdentification.user_id == User.id,
            ),
        )
        .outerjoin(
            Plant,
            Diagnosis.plant_id == Plant.id,
        )
        .where(
            VisitAppointment.status.in_(CALENDAR_ACTIVE_STATUSES),
            VisitAppointment.start_at < end,
            VisitAppointment.blocked_until > start,
        )
        .order_by(VisitAppointment.start_at)
    )

    events = []

    for appointment, diagnosis, identification, user, plant in result.all():
        status = (
            appointment.status.value
            if hasattr(appointment.status, "value")
            else appointment.status
        )

        if user is not None and (diagnosis is not None or identification is not None):
            user_name = (
                f"{user.first_name or ''} "
                f"{user.last_name or ''}"
            ).strip() or "بدون نام"

            if diagnosis is not None:
                plant_name = (
                    plant.name
                    if plant
                    else diagnosis.plant_name_input
                )
                source = diagnosis.expert_visit_source or (
                    "bale"
                    if (
                        diagnosis.telegram_file_id or ""
                    ).startswith("bale_")
                    else "legacy"
                )

                event = {
                    **_appointment_json(appointment),
                    "title": f"ویزیت {user_name}",
                    "user_id": user.id,
                    "user_name": user_name,
                    "username": user.username,
                    "phone_number": user.phone_number,
                    "plant_id": plant.id if plant else None,
                    "plant_name": plant_name,
                    "disease_name": diagnosis.disease_name,
                    "symptoms": diagnosis.symptoms,
                    "cause": diagnosis.cause,
                    "user_notes": diagnosis.user_notes,
                    "admin_notes": diagnosis.admin_notes,
                    "diagnosis_id": diagnosis.id,
                    "identification_id": None,
                    "diagnosis_status": (
                        diagnosis.visit_status.value
                        if hasattr(diagnosis.visit_status, "value")
                        else diagnosis.visit_status
                    ),
                    "calendar_status": status,
                    "source": source,
                }
            else:
                event = {
                    **_appointment_json(appointment),
                    "title": f"شناسایی گیاه - {user_name}",
                    "user_id": user.id,
                    "user_name": user_name,
                    "username": user.username,
                    "phone_number": user.phone_number,
                    "plant_id": None,
                    "plant_name": identification.persian_name or "گیاه نامشخص",
                    "disease_name": None,
                    "symptoms": None,
                    "cause": None,
                    "user_notes": None,
                    "admin_notes": identification.admin_notes,
                    "diagnosis_id": None,
                    "identification_id": identification.id,
                    "diagnosis_status": (
                        identification.visit_status.value
                        if hasattr(identification.visit_status, "value")
                        else identification.visit_status
                    ),
                    "calendar_status": status,
                    "source": identification.expert_visit_source or "legacy",
                }
        else:
            event = {
                **_appointment_json(appointment),
                "title": (
                    f"رزرو دستی - "
                    f"{appointment.customer_name or 'بدون نام'}"
                ),
                "user_id": None,
                "user_name": appointment.customer_name or "بدون نام",
                "username": None,
                "phone_number": appointment.customer_phone,
                "plant_id": None,
                "plant_name": appointment.customer_plant,
                "disease_name": None,
                "symptoms": None,
                "cause": None,
                "user_notes": None,
                "admin_notes": appointment.admin_note,
                "diagnosis_id": None,
                "identification_id": None,
                "diagnosis_status": None,
                "calendar_status": status,
                "source": "manual",
            }

        events.append(event)

    return JSONResponse(
        {
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "events": events,
        }
    )


@router.get("/api/calendar/slots")
async def calendar_slots(
    request: Request,
    start_at: str,
    end_at: str,
    step_minutes: int = DEFAULT_SLOT_STEP_MINUTES,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    if step_minutes <= 0 or step_minutes > 120:
        raise HTTPException(
            status_code=400,
            detail="step_minutes must be between 1 and 120",
        )

    start = _parse_datetime(start_at, "start_at")
    end = _parse_datetime(end_at, "end_at")

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="end_at must be after start_at",
        )

    slots = []
    cursor = start

    while cursor < end:
        slot_end = cursor + timedelta(minutes=60)

        if slot_end > end:
            break

        available = await is_slot_available(
            session=session,
            start_at=cursor,
        )

        slot_enabled = True

        slot_result = await session.execute(
            select(BookingTimeSlot)
            .where(
                BookingTimeSlot.starts_at == cursor,
                BookingTimeSlot.ends_at == slot_end,
            )
            .limit(1)
        )

        db_slot = slot_result.scalar_one_or_none()

        if db_slot is not None:
            slot_enabled = db_slot.is_enabled

        slots.append(
            {
                "start_at": cursor.isoformat(),
                "end_at": slot_end.isoformat(),
                "available": available and slot_enabled,
                "enabled": slot_enabled,
                "duration_minutes": 60,
                "buffer_minutes": 120,
            }
        )

        cursor += timedelta(minutes=step_minutes)

    return JSONResponse(
        {
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "step_minutes": step_minutes,
            "duration_minutes": 60,
            "buffer_minutes": 120,
            "slots": slots,
        }
    )


@router.post("/api/calendar/appointments")
async def calendar_create_appointment(
    request: Request,
    diagnosis_id: int,
    start_at: str,
    admin_note: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    start = _parse_datetime(start_at, "start_at")

    try:
        appointment = await create_appointment(
            session=session,
            diagnosis_id=diagnosis_id,
            start_at=start,
            admin_note=admin_note.strip() if admin_note else None,
        )

        diagnosis = await session.get(Diagnosis, diagnosis_id)

        if diagnosis is not None:
            diagnosis.visit_status = VisitStatus.SCHEDULED

        await session.commit()
        await session.refresh(appointment)

        await _send_visit_push_safe(
            title="ویزیت جدید گرین ویتا",
            body=(
                f"زمان‌بندی جدید | "
                f"{_format_visit_datetime(appointment.start_at, '%H:%M')} "
                f"تا "
                f"{_format_visit_datetime(appointment.end_at, '%H:%M')} | "
                f"Diagnosis #{diagnosis_id}"
            ),
            url="/visits",
            context={"appointment_id": appointment.id},
        )

    except AppointmentConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except SchedulerError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return JSONResponse(
        {
            "success": True,
            "appointment": _appointment_json(appointment),
        },
        status_code=201,
    )



@router.post("/api/calendar/manual-appointments")
async def calendar_create_manual_appointment(
    request: Request,
    start_at: str,
    customer_name: str,
    customer_phone: str = "",
    customer_plant: str = "",
    admin_note: str = "",
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    customer_name = customer_name.strip()

    if not customer_name:
        raise HTTPException(
            status_code=400,
            detail="نام مشتری الزامی است.",
        )

    start = _parse_datetime(start_at, "start_at")

    try:
        from src.services.visit_scheduler import calculate_window, find_conflict

        start, end, blocked_until = calculate_window(
            start,
            60,
            120,
        )

        conflict = await find_conflict(
            session=session,
            start_at=start,
            blocked_until=blocked_until,
        )

        if conflict is not None:
            raise AppointmentConflict(
                f"زمان انتخاب‌شده با رزرو {conflict.id} تداخل دارد."
            )

        booking_conflict = await find_booking_conflict(
            session=session,
            start_at=start,
            blocked_until=blocked_until,
        )

        if booking_conflict is not None:
            booking_id, _, _ = booking_conflict
            raise AppointmentConflict(
                f"زمان انتخاب‌شده با رزرو آنلاین {booking_id} تداخل دارد."
            )

        appointment = VisitAppointment(
            diagnosis_id=None,
            start_at=start,
            end_at=end,
            blocked_until=blocked_until,
            duration_minutes=60,
            buffer_minutes=120,
            status=AppointmentStatus.SCHEDULED,
            admin_note=admin_note.strip() or None,
            source="manual",
            customer_name=customer_name,
            customer_phone=customer_phone.strip() or None,
            customer_plant=customer_plant.strip() or None,
        )

        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)

        await _send_visit_push_safe(
            title="رزرو دستی جدید گرین ویتا",
            body=(
                f"{appointment.customer_name} | "
                f"{_format_visit_datetime(appointment.start_at, '%H:%M')} "
                f"تا "
                f"{_format_visit_datetime(appointment.end_at, '%H:%M')}"
            ),
            url="/visits",
            context={"appointment_id": appointment.id},
        )

    except AppointmentConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return JSONResponse(
        {
            "success": True,
            "appointment": _appointment_json(appointment),
        }
    )


@router.post("/api/calendar/appointments/{appointment_id}/reschedule")
async def calendar_reschedule_appointment(
    appointment_id: int,
    request: Request,
    start_at: str,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    start = _parse_datetime(start_at, "start_at")

    try:
        appointment = await reschedule_appointment(
            session=session,
            appointment_id=appointment_id,
            start_at=start,
        )

        diagnosis = None

        if appointment.diagnosis_id is not None:
            diagnosis = await session.get(
                Diagnosis,
                appointment.diagnosis_id,
            )

        if diagnosis is not None:
            diagnosis.visit_status = VisitStatus.SCHEDULED

        await session.commit()
        await session.refresh(appointment)

        await _send_visit_push_safe(
            title="تغییر زمان ویزیت گرین ویتا",
            body=(
                f"ویزیت #{appointment.id} به "
                f"{_format_visit_datetime(appointment.start_at, '%Y-%m-%d %H:%M')} "
                f"منتقل شد."
            ),
            url="/visits",
            context={"appointment_id": appointment.id},
        )

    except AppointmentConflict as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except AppointmentNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except SchedulerError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return JSONResponse(
        {
            "success": True,
            "appointment": _appointment_json(appointment),
        }
    )


@router.post("/api/calendar/appointments/{appointment_id}/cancel")
async def calendar_cancel_appointment(
    appointment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    try:
        appointment = await cancel_appointment(
            session=session,
            appointment_id=appointment_id,
        )

        diagnosis = None

        if appointment.diagnosis_id is not None:
            diagnosis = await session.get(
                Diagnosis,
                appointment.diagnosis_id,
            )
            if diagnosis is not None:
                diagnosis.visit_status = VisitStatus.PENDING
                diagnosis.visit_scheduled_at = None

        if getattr(appointment, "identification_id", None) is not None:
            identification = await session.get(
                PlantIdentification,
                appointment.identification_id,
            )
            if identification is not None:
                identification.visit_status = VisitStatus.PENDING
                identification.visit_scheduled_at = None

        await session.commit()
        await session.refresh(appointment)

        await _send_visit_push_safe(
            title="لغو ویزیت گرین ویتا",
            body=(
                f"ویزیت #{appointment.id} لغو شد."
            ),
            url="/visits",
            context={"appointment_id": appointment.id},
        )

    except AppointmentNotFound as exc:
        await session.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except SchedulerError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return JSONResponse(
        {
            "success": True,
            "appointment": _appointment_json(appointment),
        }
    )



@router.get("/reservations")
async def reservations_page(
    request: Request,
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "reservations.html",
        {
            "request": request,
        },
    )


@router.get("/calendar")
async def calendar_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
        },
    )


@router.get("/api/calendar/requests")
async def calendar_requests(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    requests = []

    # --------------------------------------------------------
    # Diagnosis requests waiting for scheduling
    # --------------------------------------------------------
    diagnosis_result = await session.execute(
        select(Diagnosis, User, Plant)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .outerjoin(
            VisitAppointment,
            (VisitAppointment.diagnosis_id == Diagnosis.id)
            & (VisitAppointment.status != AppointmentStatus.CANCELLED),
        )
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status.in_(
                [
                    VisitStatus.PENDING,
                    VisitStatus.REVIEWING,
                ]
            ),
            VisitAppointment.id.is_(None),
        )
        .order_by(Diagnosis.created_at.asc())
    )

    for diagnosis, user, plant in diagnosis_result.all():
        source = diagnosis.expert_visit_source or (
            "bale"
            if (diagnosis.telegram_file_id or "").startswith("bale_")
            else "telegram"
        )

        requests.append(
            {
                "kind": "diagnosis",
                "record_id": diagnosis.id,
                "diagnosis_id": diagnosis.id,
                "identification_id": None,
                "user_name": (
                    f"{user.first_name or ''} {user.last_name or ''}"
                ).strip() or "بدون نام",
                "username": user.username,
                "phone_number": user.phone_number,
                "plant_name": (
                    plant.name
                    if plant
                    else diagnosis.plant_name_input or "گیاه نامشخص"
                ),
                "disease_name": diagnosis.disease_name,
                "symptoms": diagnosis.symptoms,
                "user_notes": diagnosis.user_notes,
                "admin_notes": diagnosis.admin_notes,
                "status": (
                    diagnosis.visit_status.value
                    if hasattr(diagnosis.visit_status, "value")
                    else str(diagnosis.visit_status)
                ),
                "source": source,
                "source_label": {
                    "telegram": "✈️ تلگرام",
                    "bale": "➤ بله",
                    "legacy": "◌ قدیمی",
                }.get(source, source),
                "created_at": diagnosis.created_at.isoformat(),
            }
        )

    # --------------------------------------------------------
    # Plant identification requests waiting for scheduling
    # --------------------------------------------------------
    identification_result = await session.execute(
        select(PlantIdentification, User)
        .join(User, PlantIdentification.user_id == User.id)
        .outerjoin(
            VisitAppointment,
            (VisitAppointment.identification_id == PlantIdentification.id)
            & (VisitAppointment.status != AppointmentStatus.CANCELLED),
        )
        .where(
            PlantIdentification.expert_visit_requested.is_(True),
            PlantIdentification.visit_status.in_(
                [
                    VisitStatus.PENDING,
                    VisitStatus.REVIEWING,
                ]
            ),
            VisitAppointment.id.is_(None),
        )
        .order_by(PlantIdentification.created_at.asc())
    )

    for identification, user in identification_result.all():
        source = identification.expert_visit_source or "telegram"

        requests.append(
            {
                "kind": "identification",
                "record_id": identification.id,
                "diagnosis_id": None,
                "identification_id": identification.id,
                "user_name": (
                    f"{user.first_name or ''} {user.last_name or ''}"
                ).strip() or "بدون نام",
                "username": user.username,
                "phone_number": user.phone_number,
                "plant_name": identification.persian_name or "گیاه نامشخص",
                "disease_name": "ویزیت متخصص پس از شناسایی گیاه",
                "symptoms": None,
                "user_notes": None,
                "admin_notes": identification.admin_notes,
                "status": (
                    identification.visit_status.value
                    if hasattr(identification.visit_status, "value")
                    else str(identification.visit_status)
                ),
                "source": source,
                "source_label": {
                    "telegram": "✈️ تلگرام",
                    "bale": "➤ بله",
                    "legacy": "◌ قدیمی",
                }.get(source, source),
                "created_at": identification.created_at.isoformat(),
            }
        )

    requests.sort(
        key=lambda item: item["created_at"]
    )

    return JSONResponse({"requests": requests})


@router.get("/api/visits/pending-count")
async def pending_visits_count(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    count = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(
            Diagnosis.expert_visit_requested.is_(True),
            Diagnosis.visit_status == VisitStatus.PENDING,
        )
    )

    return JSONResponse({
        "count": count or 0,
    })


@router.get("/visits")
async def visits_list(
    request: Request,
    status: str | None = None,
    source: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    items = []

    # --------------------------------------------------------
    # Diagnosis requests
    # --------------------------------------------------------
    result = await session.execute(
        select(Diagnosis, User, Plant, VisitAppointment)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .outerjoin(
            VisitAppointment,
            (VisitAppointment.diagnosis_id == Diagnosis.id)
            & (VisitAppointment.status != AppointmentStatus.CANCELLED),
        )
        .where(Diagnosis.expert_visit_requested.is_(True))
        .order_by(Diagnosis.created_at.desc())
    )

    for diagnosis, user, plant, appointment in result.all():
        raw_status = (
            diagnosis.visit_status.value
            if hasattr(diagnosis.visit_status, "value")
            else str(diagnosis.visit_status)
        )

        raw_source = diagnosis.expert_visit_source
        if not raw_source:
            raw_source = (
                "bale"
                if (diagnosis.telegram_file_id or "").startswith("bale_")
                else "legacy"
            )

        if status and raw_status != status:
            continue
        if source and raw_source != source:
            continue

        user_name = (
            f"{user.first_name or ''} {user.last_name or ''}"
        ).strip() or "بدون نام"

        items.append(
            {
                "kind": "diagnosis",
                "id": diagnosis.id,
                "number": f"D-{diagnosis.id}",
                "user_name": user_name,
                "username": user.username,
                "phone": user.phone_number,
                "plant_name": (
                    plant.name
                    if plant
                    else diagnosis.plant_name_input or "گیاه نامشخص"
                ),
                "problem": diagnosis.disease_name,
                "notes": diagnosis.user_notes,
                "admin_notes": diagnosis.admin_notes,
                "status": raw_status,
                "status_label": STATUS_LABELS.get(raw_status, "نامشخص"),
                "status_class": STATUS_CLASSES.get(raw_status, "status-cancelled"),
                "source": raw_source,
                "source_label": {
                    "telegram": "✈️ تلگرام",
                    "bale": "➤ بله",
                    "legacy": "◌ قدیمی",
                }.get(raw_source, raw_source),
                "created_at": diagnosis.created_at,
                "scheduled_at": (
                    appointment.start_at
                    if appointment is not None
                    else diagnosis.visit_scheduled_at
                ),
                "appointment_id": appointment.id if appointment else None,
                "needs_schedule": appointment is None and raw_status in {
                    "pending",
                    "reviewing",
                },
            }
        )

    # --------------------------------------------------------
    # Plant Identification requests
    # --------------------------------------------------------
    result = await session.execute(
        select(
            PlantIdentification,
            User,
            VisitAppointment,
        )
        .join(User, PlantIdentification.user_id == User.id)
        .outerjoin(
            VisitAppointment,
            (VisitAppointment.identification_id == PlantIdentification.id)
            & (VisitAppointment.status != AppointmentStatus.CANCELLED),
        )
        .where(PlantIdentification.expert_visit_requested.is_(True))
        .order_by(PlantIdentification.created_at.desc())
    )

    for identification, user, appointment in result.all():
        raw_status = (
            identification.visit_status.value
            if hasattr(identification.visit_status, "value")
            else str(identification.visit_status)
        )

        raw_source = identification.expert_visit_source or "legacy"

        if status and raw_status != status:
            continue
        if source and raw_source != source:
            continue

        user_name = (
            f"{user.first_name or ''} {user.last_name or ''}"
        ).strip() or "بدون نام"

        items.append(
            {
                "kind": "identification",
                "id": identification.id,
                "number": f"I-{identification.id}",
                "user_name": user_name,
                "username": user.username,
                "phone": user.phone_number,
                "plant_name": identification.persian_name or "گیاه نامشخص",
                "problem": "درخواست ویزیت پس از شناسایی گیاه",
                "notes": None,
                "admin_notes": identification.admin_notes,
                "status": raw_status,
                "status_label": STATUS_LABELS.get(raw_status, "نامشخص"),
                "status_class": STATUS_CLASSES.get(raw_status, "status-cancelled"),
                "source": raw_source,
                "source_label": {
                    "telegram": "✈️ تلگرام",
                    "bale": "➤ بله",
                    "legacy": "◌ قدیمی",
                }.get(raw_source, raw_source),
                "created_at": identification.created_at,
                "scheduled_at": (
                    appointment.start_at
                    if appointment is not None
                    else identification.visit_scheduled_at
                ),
                "appointment_id": appointment.id if appointment else None,
                "needs_schedule": appointment is None and raw_status in {
                    "pending",
                    "reviewing",
                },
            }
        )

    # --------------------------------------------------------
    # Website bookings
    # --------------------------------------------------------
    booking_result = await session.execute(
        select(Booking, User, Service, BookingTimeSlot)
        .outerjoin(User, Booking.user_id == User.id)
        .join(Service, Booking.service_id == Service.id)
        .join(BookingTimeSlot, Booking.time_slot_id == BookingTimeSlot.id)
        .where(Booking.status != BookingStatus.CANCELLED)
        .order_by(Booking.created_at.desc())
    )

    for booking, user, service, time_slot in booking_result.all():
        booking_status = (
            booking.status.value
            if hasattr(booking.status, "value")
            else str(booking.status)
        )

        if status and booking_status != status:
            continue

        if source and source != "website":
            continue

        items.append(
            {
                "kind": "booking",
                "id": booking.id,
                "number": booking.tracking_code,
                "user_name": booking.customer_name,
                "username": user.username if user else None,
                "phone": booking.customer_phone,
                "plant_name": booking.plant_name or "—",
                "problem": service.title,
                "notes": booking.notes or booking.plant_description,
                "admin_notes": None,
                "status": booking_status,
                "status_label": {
                    "pending": "در انتظار تأیید",
                    "confirmed": "تأییدشده",
                    "completed": "انجام‌شده",
                    "cancelled": "لغوشده",
                }.get(booking_status, booking_status),
                "status_class": {
                    "pending": "status-pending",
                    "confirmed": "status-confirmed",
                    "completed": "status-completed",
                }.get(booking_status, "status-cancelled"),
                "source": "website",
                "source_label": "🌐 سایت",
                "created_at": booking.created_at,
                "scheduled_at": time_slot.starts_at,
                "appointment_id": None,
                "needs_schedule": False,
            }
        )

    # درخواست‌های بدون زمان همیشه بالاتر قرار بگیرند
    items.sort(
        key=lambda item: (
            0 if item["needs_schedule"] else 1,
            -(item["created_at"].timestamp() if item["created_at"] else 0),
        )
    )

    visit_counts = {
        key: 0
        for key in STATUS_LABELS.keys()
    }

    for item in items:
        if item["kind"] in {"diagnosis", "identification"}:
            if item["status"] in visit_counts:
                visit_counts[item["status"]] += 1

    booking_counts = {
        "pending": 0,
        "confirmed": 0,
        "completed": 0,
        "cancelled": 0,
    }

    for item in items:
        if item["kind"] == "booking":
            if item["status"] in booking_counts:
                booking_counts[item["status"]] += 1

    queue_needs_schedule = sum(
        1
        for item in items
        if item["kind"] in {"diagnosis", "identification"}
        and item["needs_schedule"]
    )

    queue_metrics = {
        "total": len(items),
        "needs_schedule": queue_needs_schedule,
        "scheduled": visit_counts["scheduled"] + visit_counts["confirmed"],
        "in_progress": visit_counts["in_progress"],
        "completed": visit_counts["completed"],
        "cancelled": visit_counts["cancelled"],
        "website_pending": booking_counts["pending"],
        "website_confirmed": booking_counts["confirmed"],
    }

    return templates.TemplateResponse(
        "visits.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "items": items,
            "visit_counts": visit_counts,
            "booking_counts": booking_counts,
            "queue_metrics": queue_metrics,
            "queue_needs_schedule": queue_needs_schedule,
            "status_labels": STATUS_LABELS,
            "selected_status": status,
            "selected_source": source,
        },
    )




@router.post("/api/visit-queue/{kind}/{record_id}/status")
async def unified_visit_status(
    kind: str,
    record_id: int,
    request: Request,
    status: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)

    if redirect:
        return redirect

    allowed = {
        "pending",
        "reviewing",
        "scheduled",
        "confirmed",
        "in_progress",
        "completed",
        "cancelled",
    }

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid visit status",
        )

    if kind == "diagnosis":
        obj = await session.get(Diagnosis, record_id)
        if obj is None or not obj.expert_visit_requested:
            raise HTTPException(
                status_code=404,
                detail="Visit request not found",
            )

        appointment_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.diagnosis_id == record_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )
        appointment = appointment_result.scalar_one_or_none()

        if status in {"scheduled", "confirmed", "in_progress"} and appointment is None:
            raise HTTPException(
                status_code=400,
                detail="ابتدا باید برای درخواست زمان تعیین شود.",
            )

        obj.visit_status = VisitStatus(status)

        if status == "cancelled" and appointment is not None:
            await cancel_appointment(
                session=session,
                appointment_id=appointment.id,
            )
            obj.visit_scheduled_at = None

        await session.commit()

    elif kind == "identification":
        obj = await session.get(
            PlantIdentification,
            record_id,
        )

        if obj is None or not obj.expert_visit_requested:
            raise HTTPException(
                status_code=404,
                detail="Identification visit request not found",
            )

        appointment_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.identification_id == record_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )
        appointment = appointment_result.scalar_one_or_none()

        if status in {"scheduled", "confirmed", "in_progress"} and appointment is None:
            raise HTTPException(
                status_code=400,
                detail="ابتدا باید برای درخواست زمان تعیین شود.",
            )

        obj.visit_status = VisitStatus(status)

        if status == "cancelled" and appointment is not None:
            await cancel_appointment(
                session=session,
                appointment_id=appointment.id,
            )
            obj.visit_scheduled_at = None

        await session.commit()

    elif kind == "booking":
        booking = await session.get(
            Booking,
            record_id,
        )

        if booking is None:
            raise HTTPException(
                status_code=404,
                detail="Booking not found",
            )

        booking_allowed = {
            "pending",
            "confirmed",
            "completed",
            "cancelled",
        }

        if status not in booking_allowed:
            raise HTTPException(
                status_code=400,
                detail="Invalid booking status",
            )

        booking.status = BookingStatus(status)
        await session.commit()

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid queue kind",
        )

    # AJAX / fetch clients need JSON rather than the HTML redirect.
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse(
            {
                "ok": True,
                "kind": kind,
                "record_id": record_id,
                "appointment_id": appointment.id,
                "start_at": appointment.start_at.isoformat(),
                "end_at": appointment.end_at.isoformat(),
                "status": "scheduled",
            }
        )

    return RedirectResponse(
        "/visits",
        status_code=303,
    )


@router.post("/api/visit-queue/{kind}/{record_id}/schedule")
async def unified_visit_schedule(
    kind: str,
    record_id: int,
    request: Request,
    start_at: str = Form(...),
    admin_note: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    if kind not in {"diagnosis", "identification"}:
        raise HTTPException(status_code=400, detail="Invalid visit kind")

    parsed_start = _parse_datetime(start_at, "start_at")
    clean_note = admin_note.strip() or None

    try:
        if kind == "diagnosis":
            diagnosis = await session.get(Diagnosis, record_id)

            if diagnosis is None or not diagnosis.expert_visit_requested:
                raise HTTPException(
                    status_code=404,
                    detail="Visit request not found",
                )

            existing_result = await session.execute(
                select(VisitAppointment)
                .where(
                    VisitAppointment.diagnosis_id == diagnosis.id,
                    VisitAppointment.status != AppointmentStatus.CANCELLED,
                )
                .limit(1)
            )
            existing = existing_result.scalar_one_or_none()

            if existing is None:
                appointment = await create_appointment(
                    session=session,
                    diagnosis_id=diagnosis.id,
                    start_at=parsed_start,
                    admin_note=clean_note,
                )
            else:
                appointment = await reschedule_appointment(
                    session=session,
                    appointment_id=existing.id,
                    start_at=parsed_start,
                )
                if clean_note:
                    appointment.admin_note = clean_note

            diagnosis.visit_status = VisitStatus.SCHEDULED
            diagnosis.visit_scheduled_at = appointment.start_at
            if clean_note:
                diagnosis.admin_notes = clean_note

        else:
            identification = await session.get(
                PlantIdentification,
                record_id,
            )

            if identification is None or not identification.expert_visit_requested:
                raise HTTPException(
                    status_code=404,
                    detail="Visit request not found",
                )

            existing_result = await session.execute(
                select(VisitAppointment)
                .where(
                    VisitAppointment.identification_id == identification.id,
                    VisitAppointment.status != AppointmentStatus.CANCELLED,
                )
                .limit(1)
            )
            existing = existing_result.scalar_one_or_none()

            from src.services.visit_scheduler import calculate_window, find_conflict

            start, end, blocked_until = calculate_window(
                parsed_start,
                60,
                120,
            )

            if existing is None:
                conflict = await find_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                )

                if conflict is not None:
                    raise AppointmentConflict(
                        f"زمان انتخاب‌شده با رزرو {conflict.id} تداخل دارد."
                    )

                booking_conflict = await find_booking_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                )

                if booking_conflict is not None:
                    booking_id, _, _ = booking_conflict
                    raise AppointmentConflict(
                        f"زمان انتخاب‌شده با رزرو آنلاین {booking_id} تداخل دارد."
                    )

                appointment = VisitAppointment(
                    diagnosis_id=None,
                    identification_id=identification.id,
                    start_at=start,
                    end_at=end,
                    blocked_until=blocked_until,
                    duration_minutes=60,
                    buffer_minutes=120,
                    status=AppointmentStatus.SCHEDULED,
                    admin_note=clean_note,
                    source=identification.expert_visit_source or "bot",
                )
                session.add(appointment)
                await session.flush()

            else:
                conflict = await find_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                    exclude_appointment_id=existing.id,
                )

                if conflict is not None:
                    raise AppointmentConflict(
                        f"زمان انتخاب‌شده با رزرو {conflict.id} تداخل دارد."
                    )

                booking_conflict = await find_booking_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                )

                if booking_conflict is not None:
                    booking_id, _, _ = booking_conflict
                    raise AppointmentConflict(
                        f"زمان انتخاب‌شده با رزرو آنلاین {booking_id} تداخل دارد."
                    )

                appointment = existing
                appointment.start_at = start
                appointment.end_at = end
                appointment.blocked_until = blocked_until
                appointment.admin_note = clean_note

            identification.visit_status = VisitStatus.SCHEDULED
            identification.visit_scheduled_at = appointment.start_at
            if clean_note:
                identification.admin_notes = clean_note

        await session.commit()
        await session.refresh(appointment)

    except AppointmentConflict as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    except SchedulerError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(
        "/visits",
        status_code=303,
    )



@router.get("/visits/identification/{identification_id}")
async def identification_visit_detail(
    identification_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    result = await session.execute(
        select(
            PlantIdentification,
            User,
            VisitAppointment,
        )
        .join(
            User,
            PlantIdentification.user_id == User.id,
        )
        .outerjoin(
            VisitAppointment,
            (VisitAppointment.identification_id == PlantIdentification.id)
            & (VisitAppointment.status != AppointmentStatus.CANCELLED),
        )
        .where(
            PlantIdentification.id == identification_id,
            PlantIdentification.expert_visit_requested.is_(True),
        )
        .order_by(VisitAppointment.start_at.desc())
        .limit(1)
    )

    row = result.first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Identification visit request not found",
        )

    identification, user, appointment = row

    if identification.visit_status == VisitStatus.PENDING:
        identification.visit_status = VisitStatus.REVIEWING
        await session.commit()

    return templates.TemplateResponse(
        "visit_identification_detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "identification": identification,
            "user": user,
            "appointment": appointment,
            "status_labels": STATUS_LABELS,
            "status_classes": STATUS_CLASSES,
        },
    )


@router.post("/visits/identification/{identification_id}/update")
async def update_identification_visit(
    identification_id: int,
    request: Request,
    status: str = Form(...),
    admin_note: str = Form(""),
    scheduled_at: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)

    if redirect:
        return redirect

    if status not in STATUS_LABELS:
        raise HTTPException(
            status_code=400,
            detail="Invalid visit status",
        )

    identification = await session.get(
        PlantIdentification,
        identification_id,
    )

    if (
        identification is None
        or not identification.expert_visit_requested
    ):
        raise HTTPException(
            status_code=404,
            detail="Identification visit request not found",
        )

    clean_note = admin_note.strip() or None
    identification.visit_status = VisitStatus(status)
    identification.admin_notes = clean_note

    if scheduled_at.strip():
        start_at = _parse_datetime(
            scheduled_at,
            "scheduled_at",
        )

        existing_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.identification_id == identification_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        try:
            from src.services.visit_scheduler import (
                calculate_window,
                find_conflict,
            )

            start, end, blocked_until = calculate_window(
                start_at,
                60,
                120,
            )

            if existing is None:
                conflict = await find_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                )
            else:
                conflict = await find_conflict(
                    session=session,
                    start_at=start,
                    blocked_until=blocked_until,
                    exclude_appointment_id=existing.id,
                )

            if conflict is not None:
                raise AppointmentConflict(
                    f"زمان انتخاب‌شده با ویزیت {conflict.id} تداخل دارد."
                )

            booking_conflict = await find_booking_conflict(
                session=session,
                start_at=start,
                blocked_until=blocked_until,
            )

            if booking_conflict is not None:
                booking_id, _, _ = booking_conflict
                raise AppointmentConflict(
                    f"زمان انتخاب‌شده با رزرو آنلاین {booking_id} تداخل دارد."
                )

            if existing is None:
                appointment = VisitAppointment(
                    diagnosis_id=None,
                    identification_id=identification_id,
                    start_at=start,
                    end_at=end,
                    blocked_until=blocked_until,
                    duration_minutes=60,
                    buffer_minutes=120,
                    status=AppointmentStatus.SCHEDULED,
                    admin_note=clean_note,
                    source=identification.expert_visit_source or "bot",
                )
                session.add(appointment)
                await session.flush()
            else:
                appointment = existing
                appointment.start_at = start
                appointment.end_at = end
                appointment.blocked_until = blocked_until
                appointment.admin_note = clean_note

            identification.visit_scheduled_at = appointment.start_at
            identification.visit_status = VisitStatus.SCHEDULED

        except AppointmentConflict as exc:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except SchedulerError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    else:
        existing_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.identification_id == identification_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            try:
                await cancel_appointment(
                    session=session,
                    appointment_id=existing.id,
                )
            except AppointmentNotFound as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=404,
                    detail=str(exc),
                ) from exc
            except SchedulerError as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=str(exc),
                ) from exc

        identification.visit_scheduled_at = None

    await session.commit()

    return RedirectResponse(
        f"/visits/identification/{identification_id}",
        status_code=303,
    )


@router.get("/visits/{diagnosis_id}")
async def visit_detail(
    diagnosis_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    result = await session.execute(
        select(Diagnosis, User, Plant)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.expert_visit_requested.is_(True),
        )
    )

    row = result.first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Visit request not found",
        )

    diagnosis, user, plant = row

    if diagnosis.visit_status == VisitStatus.PENDING:
        diagnosis.visit_status = VisitStatus.REVIEWING
        await session.commit()

    appointment_result = await session.execute(
        select(VisitAppointment)
        .where(
            VisitAppointment.diagnosis_id == diagnosis_id,
            VisitAppointment.status != AppointmentStatus.CANCELLED,
        )
        .order_by(VisitAppointment.start_at.desc())
        .limit(1)
    )

    appointment = appointment_result.scalar_one_or_none()

    return templates.TemplateResponse(
        "visit_detail.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "diagnosis": diagnosis,
            "user": user,
            "plant": plant,
            "appointment": appointment,
            "status_labels": STATUS_LABELS,
            "status_classes": STATUS_CLASSES,
        },
    )


@router.post("/visits/{diagnosis_id}/update")
async def update_visit(
    diagnosis_id: int,
    request: Request,
    status: str = Form(...),
    admin_note: str = Form(""),
    scheduled_at: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)

    if redirect:
        return redirect

    if status not in STATUS_LABELS:
        raise HTTPException(
            status_code=400,
            detail="Invalid visit status",
        )

    diagnosis = await session.get(
        Diagnosis,
        diagnosis_id,
    )

    if not diagnosis or not diagnosis.expert_visit_requested:
        raise HTTPException(
            status_code=404,
            detail="Visit request not found",
        )

    diagnosis.visit_status = VisitStatus(status)
    diagnosis.admin_notes = admin_note.strip() or None

    if scheduled_at.strip():
        start_at = _parse_datetime(
            scheduled_at,
            "scheduled_at",
        )

        existing_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.diagnosis_id == diagnosis_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )

        existing = existing_result.scalar_one_or_none()

        try:
            if existing is None:
                appointment = await create_appointment(
                    session=session,
                    diagnosis_id=diagnosis_id,
                    start_at=start_at,
                    admin_note=admin_note.strip() or None,
                )
            else:
                appointment = await reschedule_appointment(
                    session=session,
                    appointment_id=existing.id,
                    start_at=start_at,
                )

            diagnosis.visit_scheduled_at = appointment.start_at
            diagnosis.visit_status = VisitStatus.SCHEDULED

        except AppointmentConflict as exc:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except SchedulerError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    else:
        existing_result = await session.execute(
            select(VisitAppointment)
            .where(
                VisitAppointment.diagnosis_id == diagnosis_id,
                VisitAppointment.status != AppointmentStatus.CANCELLED,
            )
            .limit(1)
        )

        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            try:
                await cancel_appointment(
                    session=session,
                    appointment_id=existing.id,
                )
            except AppointmentNotFound as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=404,
                    detail=str(exc),
                ) from exc
            except SchedulerError as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=str(exc),
                ) from exc

        diagnosis.visit_scheduled_at = None

    await session.commit()

    return RedirectResponse(
        "/visits",
        status_code=303,
    )
