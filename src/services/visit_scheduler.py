from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.diagnosis import Diagnosis
from src.db.models.visit_status import VisitStatus
from src.db.models.visit_appointment import (
    AppointmentStatus,
    VisitAppointment,
)


DEFAULT_DURATION_MINUTES = 60
DEFAULT_BUFFER_MINUTES = 120

ACTIVE_STATUSES = (
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.IN_PROGRESS,
)


class SchedulerError(Exception):
    """Base exception for visit scheduling errors."""


class InvalidAppointmentTime(SchedulerError):
    pass


class AppointmentConflict(SchedulerError):
    pass


class AppointmentNotFound(SchedulerError):
    pass


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise InvalidAppointmentTime(
            "Appointment datetime must be timezone-aware."
        )
    return value.astimezone(timezone.utc)


def calculate_window(
    start_at: datetime,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
) -> tuple[datetime, datetime, datetime]:
    if duration_minutes <= 0:
        raise InvalidAppointmentTime("Duration must be greater than zero.")

    if buffer_minutes < 0:
        raise InvalidAppointmentTime("Buffer cannot be negative.")

    start_at = ensure_utc(start_at)
    end_at = start_at + timedelta(minutes=duration_minutes)
    blocked_until = end_at + timedelta(minutes=buffer_minutes)

    return start_at, end_at, blocked_until


async def find_conflict(
    session: AsyncSession,
    start_at: datetime,
    blocked_until: datetime,
    exclude_appointment_id: int | None = None,
) -> VisitAppointment | None:
    conditions = [
        VisitAppointment.status.in_(ACTIVE_STATUSES),
        VisitAppointment.start_at < blocked_until,
        VisitAppointment.blocked_until > start_at,
    ]

    if exclude_appointment_id is not None:
        conditions.append(
            VisitAppointment.id != exclude_appointment_id
        )

    result = await session.execute(
        select(VisitAppointment)
        .where(and_(*conditions))
        .order_by(VisitAppointment.start_at)
        .limit(1)
    )

    return result.scalar_one_or_none()


async def is_slot_available(
    session: AsyncSession,
    start_at: datetime,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
    exclude_appointment_id: int | None = None,
) -> bool:
    _, _, blocked_until = calculate_window(
        start_at,
        duration_minutes,
        buffer_minutes,
    )

    start_at = ensure_utc(start_at)

    conflict = await find_conflict(
        session=session,
        start_at=start_at,
        blocked_until=blocked_until,
        exclude_appointment_id=exclude_appointment_id,
    )

    return conflict is None


async def create_appointment(
    session: AsyncSession,
    diagnosis_id: int,
    start_at: datetime,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
    admin_note: str | None = None,
) -> VisitAppointment:
    start_at, end_at, blocked_until = calculate_window(
        start_at,
        duration_minutes,
        buffer_minutes,
    )

    diagnosis = await session.get(Diagnosis, diagnosis_id)

    if diagnosis is None:
        raise SchedulerError(
            f"Diagnosis {diagnosis_id} was not found."
        )

    existing = await session.execute(
        select(VisitAppointment)
        .where(
            VisitAppointment.diagnosis_id == diagnosis_id,
            VisitAppointment.status != AppointmentStatus.CANCELLED,
        )
        .limit(1)
    )

    if existing.scalar_one_or_none() is not None:
        raise SchedulerError(
            f"Diagnosis {diagnosis_id} already has an active appointment."
        )

    conflict = await find_conflict(
        session=session,
        start_at=start_at,
        blocked_until=blocked_until,
    )

    if conflict is not None:
        raise AppointmentConflict(
            f"Requested slot conflicts with appointment "
            f"{conflict.id}."
        )

    appointment = VisitAppointment(
        diagnosis_id=diagnosis_id,
        start_at=start_at,
        end_at=end_at,
        blocked_until=blocked_until,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
        status=AppointmentStatus.SCHEDULED,
        admin_note=admin_note,
    )

    session.add(appointment)

    diagnosis.visit_scheduled_at = start_at

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppointmentConflict(
            "The requested slot is no longer available."
        ) from exc

    return appointment


async def reschedule_appointment(
    session: AsyncSession,
    appointment_id: int,
    start_at: datetime,
    duration_minutes: int | None = None,
    buffer_minutes: int | None = None,
) -> VisitAppointment:
    appointment = await session.get(
        VisitAppointment,
        appointment_id,
    )

    if appointment is None:
        raise AppointmentNotFound(
            f"Appointment {appointment_id} was not found."
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise SchedulerError(
            "Cancelled appointments cannot be rescheduled."
        )

    duration = (
        duration_minutes
        if duration_minutes is not None
        else appointment.duration_minutes
    )

    buffer = (
        buffer_minutes
        if buffer_minutes is not None
        else appointment.buffer_minutes
    )

    start_at, end_at, blocked_until = calculate_window(
        start_at,
        duration,
        buffer,
    )

    conflict = await find_conflict(
        session=session,
        start_at=start_at,
        blocked_until=blocked_until,
        exclude_appointment_id=appointment.id,
    )

    if conflict is not None:
        raise AppointmentConflict(
            f"Requested slot conflicts with appointment "
            f"{conflict.id}."
        )

    appointment.start_at = start_at
    appointment.end_at = end_at
    appointment.blocked_until = blocked_until
    appointment.duration_minutes = duration
    appointment.buffer_minutes = buffer

    diagnosis = await session.get(
        Diagnosis,
        appointment.diagnosis_id,
    )

    if diagnosis is not None:
        diagnosis.visit_scheduled_at = start_at

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppointmentConflict(
            "The requested slot is no longer available."
        ) from exc

    return appointment


async def cancel_appointment(
    session: AsyncSession,
    appointment_id: int,
) -> VisitAppointment:
    appointment = await session.get(
        VisitAppointment,
        appointment_id,
    )

    if appointment is None:
        raise AppointmentNotFound(
            f"Appointment {appointment_id} was not found."
        )

    appointment.status = AppointmentStatus.CANCELLED

    diagnosis = await session.get(
        Diagnosis,
        appointment.diagnosis_id,
    )

    if diagnosis is not None:
        diagnosis.visit_scheduled_at = None
        diagnosis.visit_status = VisitStatus.PENDING

    await session.flush()

    return appointment


async def get_appointment(
    session: AsyncSession,
    appointment_id: int,
) -> VisitAppointment:
    appointment = await session.get(
        VisitAppointment,
        appointment_id,
    )

    if appointment is None:
        raise AppointmentNotFound(
            f"Appointment {appointment_id} was not found."
        )

    return appointment


async def list_appointments(
    session: AsyncSession,
    start_at: datetime,
    end_at: datetime,
) -> list[VisitAppointment]:
    start_at = ensure_utc(start_at)
    end_at = ensure_utc(end_at)

    if end_at <= start_at:
        raise InvalidAppointmentTime(
            "Calendar end must be after calendar start."
        )

    result = await session.execute(
        select(VisitAppointment)
        .where(
            and_(
                VisitAppointment.status.in_(ACTIVE_STATUSES),
                VisitAppointment.start_at < end_at,
                VisitAppointment.blocked_until > start_at,
            )
        )
        .order_by(VisitAppointment.start_at)
    )

    return list(result.scalars().all())
