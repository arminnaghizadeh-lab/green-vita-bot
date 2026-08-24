from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, User
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)
from src.db.models.visit_status import VisitStatus
from src.services.visit_scheduler import (
    AppointmentConflict,
    AppointmentNotFound,
    InvalidAppointmentTime,
    SchedulerError,
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


def _parse_datetime(value: str, field_name: str) -> datetime:
    value = value.strip()

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}",
        ) from exc

    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must include timezone information",
        )

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
        select(VisitAppointment, Diagnosis, User, Plant)
        .join(
            Diagnosis,
            VisitAppointment.diagnosis_id == Diagnosis.id,
        )
        .join(
            User,
            Diagnosis.user_id == User.id,
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

    for appointment, diagnosis, user, plant in result.all():
        status = (
            appointment.status.value
            if hasattr(appointment.status, "value")
            else appointment.status
        )

        events.append(
            {
                **_appointment_json(appointment),
                "title": (
                    f"ویزیت {user.first_name or ''} "
                    f"{user.last_name or ''}"
                ).strip(),
                "user_id": user.id,
                "user_name": (
                    f"{user.first_name or ''} "
                    f"{user.last_name or ''}"
                ).strip(),
                "plant_id": plant.id if plant else None,
                "plant_name": plant.name if plant else None,
                "diagnosis_status": (
                    diagnosis.visit_status.value
                    if hasattr(diagnosis.visit_status, "value")
                    else diagnosis.visit_status
                ),
                "calendar_status": status,
            }
        )

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

        slots.append(
            {
                "start_at": cursor.isoformat(),
                "end_at": slot_end.isoformat(),
                "available": available,
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

        diagnosis = await session.get(
            Diagnosis,
            appointment.diagnosis_id,
        )

        if diagnosis is not None:
            diagnosis.visit_status = VisitStatus.SCHEDULED

        await session.commit()
        await session.refresh(appointment)

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

    appointment = await session.get(
        VisitAppointment,
        appointment_id,
    )

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found",
        )

    appointment.status = AppointmentStatus.CANCELLED

    diagnosis = await session.get(
        Diagnosis,
        appointment.diagnosis_id,
    )

    if diagnosis is not None:
        diagnosis.visit_scheduled_at = None
        diagnosis.visit_status = VisitStatus.CANCELLED

    await session.commit()

    return JSONResponse(
        {
            "success": True,
            "appointment": _appointment_json(appointment),
        }
    )


@router.get("/visits")
async def visits_list(
    request: Request,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    query = (
        select(Diagnosis, User, Plant)
        .join(User, Diagnosis.user_id == User.id)
        .outerjoin(Plant, Diagnosis.plant_id == Plant.id)
        .where(Diagnosis.expert_visit_requested.is_(True))
        .order_by(
            Diagnosis.visit_scheduled_at.desc().nullslast(),
            Diagnosis.created_at.desc(),
        )
    )

    if status in STATUS_LABELS:
        query = query.where(Diagnosis.visit_status == status)

    rows = (await session.execute(query)).all()

    visits = [
        {
            "diagnosis": diagnosis,
            "user": user,
            "plant": plant,
            "status_label": STATUS_LABELS.get(
                diagnosis.visit_status.value
                if hasattr(diagnosis.visit_status, "value")
                else diagnosis.visit_status,
                "نامشخص",
            ),
            "status_class": STATUS_CLASSES.get(
                diagnosis.visit_status.value
                if hasattr(diagnosis.visit_status, "value")
                else diagnosis.visit_status,
                "status-cancelled",
            ),
        }
        for diagnosis, user, plant in rows
    ]

    counts_result = await session.execute(
        select(Diagnosis.visit_status, func.count())
        .where(Diagnosis.expert_visit_requested.is_(True))
        .group_by(Diagnosis.visit_status)
    )

    counts = {}

    for row in counts_result.all():
        key = row[0].value if hasattr(row[0], "value") else row[0]
        counts[key] = row[1]

    return templates.TemplateResponse(
        "visits.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "visits": visits,
            "counts": counts,
            "status_labels": STATUS_LABELS,
            "selected_status": status,
        },
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
            existing.status = AppointmentStatus.CANCELLED

        diagnosis.visit_scheduled_at = None

    await session.commit()

    return RedirectResponse(
        "/visits",
        status_code=303,
    )
