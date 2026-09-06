from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import jdatetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from src.db.models.booking import (
    Booking,
    BookingSchedule,
    BookingSlotAssignment,
    BookingSource,
    BookingStatus,
    BookingTimeSlot,
    Service,
)
from src.db.session import AsyncSessionLocal
from src.admin.services.push import send_push
from src.services.appointment_availability import (
    get_visit_occupied_slot_starts,
)

router = APIRouter(prefix="/booking", tags=["booking"])
templates = Jinja2Templates(directory="src/admin/templates")

TEHRAN = ZoneInfo("Asia/Tehran")
BUFFER_HOURS = 2
MAX_BOOKING_START_HOUR = 17
MAX_BOOKING_DURATION_HOURS = 3

PHONE_CONSULTATION_SERVICE_ID = 4
PHONE_CONSULTATION_BUFFER_HOURS = 1
PHONE_CONSULTATION_MAX_DURATION_HOURS = 1


async def _send_booking_push_safe(
    *,
    title: str,
    body: str,
    url: str = "/dashboard/",
    context: dict | None = None,
) -> None:
    """
    Push خطا نباید روی transaction اصلی Booking اثر بگذارد.
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
            "booking_admin_push_failed",
            extra=context or {},
        )


def generate_tracking_code() -> str:
    return "GV-" + secrets.token_hex(5).upper()


def jalali_to_tehran_date(jalali_date: str):
    try:
        jy, jm, jd = map(int, jalali_date.split("-"))

        return jdatetime.datetime(
            jy,
            jm,
            jd,
            0,
            0,
            0,
            tzinfo=TEHRAN,
        ).togregorian()

    except (ValueError, TypeError):
        return None


def available_durations(
    slots: list[BookingTimeSlot],
    start_index: int,
    occupied_starts: set[datetime] | None = None,
    max_duration_hours: int = MAX_BOOKING_DURATION_HOURS,
    buffer_hours: int = BUFFER_HOURS,
) -> list[int]:
    """
    مدت‌های قابل رزرو برای Slot شروع.

    قوانین:
    - آخرین زمان شروع رزرو: 17:00
    - مدت رزرو: فقط 1، 2 یا 3 ساعت
    - Slotهای رزرو باید متوالی و آزاد باشند
    - 2 ساعت Buffer بعد از پایان ویزیت باید آزاد باشد
    """

    durations: list[int] = []
    occupied_starts = occupied_starts or set()

    def slot_is_free(slot: BookingTimeSlot) -> bool:
        return (
            slot.is_available
            and slot.starts_at not in occupied_starts
        )

    if start_index >= len(slots):
        return durations

    start_slot = slots[start_index]
    local_start = start_slot.starts_at.astimezone(TEHRAN)

    if (
        local_start.hour > MAX_BOOKING_START_HOUR
        or (
            local_start.hour == MAX_BOOKING_START_HOUR
            and local_start.minute > 0
        )
    ):
        return durations

    for hours in range(1, max_duration_hours + 1):
        reserved = slots[
            start_index:start_index + hours
        ]

        if len(reserved) != hours:
            break

        if not all(
            slot_is_free(slot)
            for slot in reserved
        ):
            break

        contiguous = True

        for i in range(1, len(reserved)):
            previous = reserved[i - 1]
            current = reserved[i]

            if current.starts_at != previous.ends_at:
                contiguous = False
                break

        if not contiguous:
            break

        end_at = reserved[-1].ends_at

        buffer_slots = [
            slot
            for slot in slots
            if (
                slot.starts_at >= end_at
                and slot.starts_at
                < end_at + timedelta(hours=buffer_hours)
            )
        ]

        if len(buffer_slots) != buffer_hours:
            break

        buffer_contiguous = True

        for i in range(1, len(buffer_slots)):
            previous = buffer_slots[i - 1]
            current = buffer_slots[i]

            if current.starts_at != previous.ends_at:
                buffer_contiguous = False
                break

        if not buffer_contiguous:
            break

        if not all(
            slot_is_free(slot)
            for slot in buffer_slots
        ):
            break

        durations.append(hours)

    return durations



async def get_shared_occupied_starts(
    session: AsyncSession,
    start_g: datetime,
    end_g: datetime,
    exclude_booking_id: int | None = None,
) -> set[datetime]:
    """
    تمام زمان‌های اشغال‌شده در کل خدمات.

    فقط رزروهای PENDING و CONFIRMED ظرفیت را اشغال می‌کنند.
    بنابراین Assignmentهای باقی‌مانده از CANCELLED مانع رزرو نمی‌شوند.
    """
    stmt = (
        select(BookingTimeSlot.starts_at)
        .join(
            BookingSlotAssignment,
            BookingSlotAssignment.time_slot_id
            == BookingTimeSlot.id,
        )
        .join(
            Booking,
            Booking.id == BookingSlotAssignment.booking_id,
        )
        .where(
            BookingTimeSlot.starts_at >= start_g,
            BookingTimeSlot.starts_at < end_g,
            Booking.status.in_(
                (
                    BookingStatus.PENDING,
                    BookingStatus.CONFIRMED,
                )
            ),
        )
    )

    if exclude_booking_id is not None:
        stmt = stmt.where(
            Booking.id != exclude_booking_id
        )

    result = await session.execute(stmt)

    booking_occupied_starts = set(result.scalars().all())

    visit_occupied_starts = await get_visit_occupied_slot_starts(
        session,
        start_g,
        end_g,
    )

    return booking_occupied_starts | visit_occupied_starts


@router.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def booking_home(request: Request):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service)
            .where(Service.is_active.is_(True))
            .order_by(Service.id)
        )

        services = result.scalars().all()

    return templates.TemplateResponse(
        "booking/index.html",
        {
            "request": request,
            "services": services,
        },
    )


@router.get(
    "/track/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def booking_track_page(request: Request):
    return templates.TemplateResponse(
        "booking/track.html",
        {
            "request": request,
        },
    )


@router.post("/api/track", include_in_schema=False)
async def booking_track(
    tracking_code: str = Form(...),
    customer_phone: str = Form(...),
):
    tracking_code = tracking_code.strip().upper()
    customer_phone = customer_phone.strip()

    if not tracking_code or not customer_phone:
        return {
            "success": False,
            "error": "کد رهگیری و شماره تماس را وارد کنید.",
        }

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                Booking,
                Service,
                BookingTimeSlot,
            )
            .join(
                Service,
                Booking.service_id == Service.id,
            )
            .join(
                BookingTimeSlot,
                Booking.time_slot_id == BookingTimeSlot.id,
            )
            .where(
                Booking.tracking_code == tracking_code,
                Booking.customer_phone == customer_phone,
            )
        )

        row = result.first()

        if row is None:
            return {
                "success": False,
                "error": "رزروی با این کد رهگیری و شماره تماس پیدا نشد.",
            }

        booking, service, start_slot = row

        assignment_result = await session.execute(
            select(BookingSlotAssignment)
            .where(
                BookingSlotAssignment.booking_id == booking.id,
                BookingSlotAssignment.kind == "RESERVED",
            )
            .order_by(BookingSlotAssignment.time_slot_id)
        )

        reserved_assignments = assignment_result.scalars().all()

        duration_hours = len(reserved_assignments)

        start_local = start_slot.starts_at.astimezone(TEHRAN)

        end_local = (
            start_slot.starts_at
            + timedelta(hours=duration_hours)
        ).astimezone(TEHRAN)

        now_tehran = datetime.now(TEHRAN)

        can_edit = (
            start_local > now_tehran + timedelta(hours=24)
            and booking.status not in (
                BookingStatus.CANCELLED,
                BookingStatus.COMPLETED,
            )
        )

        return {
            "success": True,
            "booking": {
                "id": booking.id,
                "tracking_code": booking.tracking_code,
                "service_id": service.id,
                "time_slot_id": start_slot.id,
                "service_title": service.title,
                "status": booking.status.value,
                "customer_name": booking.customer_name,
                "customer_phone": booking.customer_phone,
                "customer_email": booking.customer_email or "",
                "plant_name": booking.plant_name or "",
                "plant_description": booking.plant_description or "",
                "notes": booking.notes or "",
                "date": start_local.strftime("%Y-%m-%d"),
                "start_time": start_local.strftime("%H:%M"),
                "end_time": end_local.strftime("%H:%M"),
                "duration_hours": duration_hours,
                "amount": int(booking.final_amount),
                "can_edit": can_edit,
            },
        }


@router.get(
    "/service/{service_id}/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def booking_service(
    request: Request,
    service_id: int,
):
    async with AsyncSessionLocal() as session:
        service = await session.get(Service, service_id)

    if service is None or not service.is_active:
        return HTMLResponse(
            "خدمت موردنظر پیدا نشد.",
            status_code=404,
        )

    return templates.TemplateResponse(
        "booking/service.html",
        {
            "request": request,
            "service": service,
        },
    )


@router.get(
    "/service/{service_id}/preview/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def booking_preview(
    request: Request,
    service_id: int,
):
    async with AsyncSessionLocal() as session:
        service = await session.get(Service, service_id)

    if service is None or not service.is_active:
        return HTMLResponse(
            "خدمت موردنظر پیدا نشد.",
            status_code=404,
        )

    return templates.TemplateResponse(
        "booking/preview.html",
        {
            "request": request,
            "service": service,
        },
    )


@router.get("/api/services", include_in_schema=False)
async def booking_services():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service)
            .where(Service.is_active.is_(True))
            .order_by(Service.id)
        )

        services = result.scalars().all()

    return [
        {
            "id": service.id,
            "title": service.title,
            "slug": service.slug,
            "price": int(service.price),
            "duration_minutes": service.duration_minutes,
            "image_url": service.image_url,
        }
        for service in services
    ]


@router.get(
    "/api/slots/{service_id}/{jalali_date}",
    include_in_schema=False,
)
async def booking_slots(
    service_id: int,
    jalali_date: str,
):
    start_g = jalali_to_tehran_date(jalali_date)

    if start_g is None:
        return {
            "error": "تاریخ نامعتبر است.",
            "slots": [],
        }

    end_g = start_g + timedelta(days=1)
    now_tehran = datetime.now(TEHRAN)

    async with AsyncSessionLocal() as session:
        service = await session.get(Service, service_id)

        if service is None or not service.is_active:
            return {
                "error": "خدمت موردنظر پیدا نشد.",
                "slots": [],
            }

        result = await session.execute(
            select(BookingTimeSlot)
            .join(BookingSchedule)
            .where(
                BookingSchedule.service_id == service_id,
                BookingTimeSlot.starts_at >= start_g,
                BookingTimeSlot.starts_at < end_g,
            )
            .order_by(BookingTimeSlot.starts_at)
        )

        db_slots = result.scalars().all()

        shared_occupied_starts = await get_shared_occupied_starts(
            session,
            start_g,
            end_g,
        )

        max_duration_hours = (
            PHONE_CONSULTATION_MAX_DURATION_HOURS
            if service_id == PHONE_CONSULTATION_SERVICE_ID
            else MAX_BOOKING_DURATION_HOURS
        )

        buffer_hours = (
            PHONE_CONSULTATION_BUFFER_HOURS
            if service_id == PHONE_CONSULTATION_SERVICE_ID
            else BUFFER_HOURS
        )

        # فقط Slotهای آینده آزاد به UI نمایش داده می‌شوند.
        if start_g.date() == now_tehran.date():
            db_slots = [
                slot
                for slot in db_slots
                if slot.starts_at > now_tehran
            ]

        # همه Slotها برای محاسبه پیوستگی لازم‌اند.
        available_slots = db_slots

        output = []

        for index, slot in enumerate(available_slots):
            if not slot.is_available:
                continue

            durations = available_durations(
                available_slots,
                index,
                shared_occupied_starts,
                max_duration_hours,
                buffer_hours,
            )

            if not durations:
                continue

            local_start = slot.starts_at.astimezone(TEHRAN)

            if (
                local_start.hour > MAX_BOOKING_START_HOUR
                or (
                    local_start.hour == MAX_BOOKING_START_HOUR
                    and local_start.minute > 0
                )
            ):
                continue

            output.append(
                {
                    "id": slot.id,
                    "date": local_start.strftime("%Y-%m-%d"),
                    "time": local_start.strftime("%H:%M"),
                    "starts_at": local_start.isoformat(),
                    "available_durations": [
                        {
                            "hours": hours,
                            "end_time": (
                                slot.starts_at
                                + timedelta(hours=hours)
                            )
                            .astimezone(TEHRAN)
                            .strftime("%H:%M"),
                            "amount": int(
                                Decimal(str(service.price or 0))
                                * hours
                            ),
                        }
                        for hours in durations
                    ],
                }
            )

    return {
        "service_id": service_id,
        "date": jalali_date,
        "slots": output,
    }




@router.post("/api/edit", include_in_schema=False)
async def edit_booking(
    booking_id: int = Form(...),
    tracking_code: str = Form(...),
    customer_phone: str = Form(...),
    service_id: int = Form(...),
    slot_id: int = Form(...),
    duration_hours: int = Form(...),
    customer_name: str = Form(...),
    customer_email: str = Form(""),
    plant_name: str = Form(""),
    plant_description: str = Form(""),
    notes: str = Form(""),
):
    tracking_code = tracking_code.strip().upper()
    customer_phone = customer_phone.strip()
    customer_name = customer_name.strip()
    customer_email = customer_email.strip() or None
    plant_name = plant_name.strip() or None
    plant_description = plant_description.strip() or None
    notes = notes.strip() or None

    if not customer_name or not customer_phone:
        return {
            "success": False,
            "error": "نام و شماره تماس الزامی است.",
        }

    if not tracking_code:
        return {
            "success": False,
            "error": "کد رهگیری الزامی است.",
        }

    if (
        duration_hours < 1
        or duration_hours > MAX_BOOKING_DURATION_HOURS
    ):
        return {
            "success": False,
            "error": "مدت رزرو فقط بین ۱ تا ۳ ساعت مجاز است.",
        }

    async with AsyncSessionLocal() as session:
        async with session.begin():

            booking_result = await session.execute(
                select(Booking)
                .where(
                    Booking.id == booking_id,
                    Booking.tracking_code == tracking_code,
                    Booking.customer_phone == customer_phone,
                )
                .with_for_update()
            )

            booking = booking_result.scalar_one_or_none()

            if booking is None:
                return {
                    "success": False,
                    "error": "رزرو موردنظر پیدا نشد.",
                }

            if booking.status in (
                BookingStatus.CANCELLED,
                BookingStatus.COMPLETED,
            ):
                return {
                    "success": False,
                    "error": "این رزرو قابل ویرایش نیست.",
                }

            current_slot = await session.get(
                BookingTimeSlot,
                booking.time_slot_id,
            )

            if current_slot is None:
                return {
                    "success": False,
                    "error": "زمان رزرو فعلی پیدا نشد.",
                }

            current_start = current_slot.starts_at.astimezone(TEHRAN)
            now_tehran = datetime.now(TEHRAN)

            if (
                current_start
                <= now_tehran + timedelta(hours=24)
            ):
                return {
                    "success": False,
                    "error": (
                        "ویرایش رزرو فقط تا ۲۴ ساعت قبل "
                        "از زمان شروع امکان‌پذیر است."
                    ),
                }

            service = await session.get(
                Service,
                service_id,
            )

            if service is None or not service.is_active:
                return {
                    "success": False,
                    "error": "خدمت موردنظر پیدا نشد.",
                }

            max_duration_hours = (
                PHONE_CONSULTATION_MAX_DURATION_HOURS
                if service.id == PHONE_CONSULTATION_SERVICE_ID
                else MAX_BOOKING_DURATION_HOURS
            )

            buffer_hours = (
                PHONE_CONSULTATION_BUFFER_HOURS
                if service.id == PHONE_CONSULTATION_SERVICE_ID
                else BUFFER_HOURS
            )

            if duration_hours > max_duration_hours:
                return {
                    "success": False,
                    "error": (
                        "برای مشاوره تلفنی تخصصی فقط ۱ ساعت قابل رزرو است."
                        if service.id == PHONE_CONSULTATION_SERVICE_ID
                        else "مدت رزرو فقط بین ۱ تا ۳ ساعت مجاز است."
                    ),
                }

            start_result = await session.execute(
                select(BookingTimeSlot)
                .join(BookingSchedule)
                .where(
                    BookingTimeSlot.id == slot_id,
                    BookingSchedule.service_id == service_id,
                )
                .with_for_update()
            )

            start_slot = start_result.scalar_one_or_none()

            if start_slot is None:
                return {
                    "success": False,
                    "error": "زمان شروع انتخاب‌شده پیدا نشد.",
                }

            new_local_start = start_slot.starts_at.astimezone(TEHRAN)

            if (
                new_local_start.hour > MAX_BOOKING_START_HOUR
                or (
                    new_local_start.hour == MAX_BOOKING_START_HOUR
                    and new_local_start.minute > 0
                )
            ):
                return {
                    "success": False,
                    "error": "شروع رزرو حداکثر تا ساعت 17:00 مجاز است.",
                }

            if start_slot.starts_at <= now_tehran:
                return {
                    "success": False,
                    "error": "زمان انتخاب‌شده گذشته است.",
                }

            schedule = await session.get(
                BookingSchedule,
                start_slot.schedule_id,
            )

            if schedule is None:
                return {
                    "success": False,
                    "error": "برنامه زمانی پیدا نشد.",
                }

            # تمام Slotهای رزرو قبلی این Booking را قفل و آزاد می‌کنیم.
            old_assignments_result = await session.execute(
                select(BookingSlotAssignment)
                .where(
                    BookingSlotAssignment.booking_id == booking.id
                )
                .with_for_update()
            )

            old_assignments = old_assignments_result.scalars().all()

            for assignment in old_assignments:
                old_slot = await session.get(
                    BookingTimeSlot,
                    assignment.time_slot_id,
                )

                if old_slot is not None:
                    old_slot.is_available = True

            total_slots = duration_hours + buffer_hours

            shared_end = (
                start_slot.starts_at
                + timedelta(hours=total_slots)
            )

            # قفل ظرفیت زمانی مشترک کل خدمات
            await session.execute(
                select(BookingTimeSlot.id)
                .where(
                    BookingTimeSlot.starts_at >= start_slot.starts_at,
                    BookingTimeSlot.starts_at < shared_end,
                )
                .with_for_update()
            )

            shared_occupied_starts = await get_shared_occupied_starts(
                session,
                start_slot.starts_at,
                shared_end,
                exclude_booking_id=booking.id,
            )

            if any(
                slot_start in shared_occupied_starts
                for slot_start in (
                    start_slot.starts_at
                    + timedelta(hours=i)
                    for i in range(total_slots)
                )
            ):
                return {
                    "success": False,
                    "error": (
                        "بخشی از بازه انتخابی یا دو ساعت بافر "
                        "در یکی از خدمات دیگر رزرو شده است."
                    ),
                }

            new_slots_result = await session.execute(
                select(BookingTimeSlot)
                .where(
                    BookingTimeSlot.schedule_id == schedule.id,
                    BookingTimeSlot.starts_at >= start_slot.starts_at,
                    BookingTimeSlot.starts_at
                    < start_slot.starts_at
                    + timedelta(hours=total_slots),
                )
                .order_by(BookingTimeSlot.starts_at)
                .with_for_update()
            )

            locked_slots = new_slots_result.scalars().all()

            if len(locked_slots) != total_slots:
                return {
                    "success": False,
                    "error": (
                        "برای این مدت، بازه کامل "
                        "و دو ساعت فاصله بعدی موجود نیست."
                    ),
                }

            for index in range(1, len(locked_slots)):
                previous = locked_slots[index - 1]
                current = locked_slots[index]

                if current.starts_at != previous.ends_at:
                    return {
                        "success": False,
                        "error": (
                            "ساعات انتخاب‌شده باید کاملاً متوالی باشند."
                        ),
                    }

            if not all(
                slot.is_available
                for slot in locked_slots
            ):
                return {
                    "success": False,
                    "error": "بخشی از زمان انتخاب‌شده قبلاً رزرو شده است.",
                }

            reserved_slots = locked_slots[:duration_hours]
            buffer_slots = locked_slots[duration_hours:]

            # Assignmentهای قبلی حذف می‌شوند.
            for assignment in old_assignments:
                await session.delete(assignment)

            # قبل از ایجاد Assignmentهای جدید، DELETEهای قبلی
            # حتماً به دیتابیس flush شوند تا محدودیت یکتا روی
            # time_slot_id مانع درج Slot جدید نشود.
            await session.flush()

            booking.service_id = service.id
            booking.time_slot_id = start_slot.id
            booking.customer_name = customer_name
            booking.customer_email = customer_email
            booking.plant_name = plant_name
            booking.plant_description = plant_description
            booking.notes = notes

            base_amount = (
                Decimal(str(service.price or 0))
                * duration_hours
            )

            booking.base_amount = base_amount
            booking.discount_amount = Decimal("0")
            booking.final_amount = base_amount

            new_assignments = []

            for slot in reserved_slots:
                new_assignments.append(
                    BookingSlotAssignment(
                        booking_id=booking.id,
                        time_slot_id=slot.id,
                        kind="RESERVED",
                    )
                )
                slot.is_available = False

            for slot in buffer_slots:
                new_assignments.append(
                    BookingSlotAssignment(
                        booking_id=booking.id,
                        time_slot_id=slot.id,
                        kind="BUFFER",
                    )
                )
                slot.is_available = False

            session.add_all(new_assignments)

            end_time = (
                reserved_slots[-1].ends_at
                .astimezone(TEHRAN)
                .strftime("%H:%M")
            )

            start_time = (
                reserved_slots[0].starts_at
                .astimezone(TEHRAN)
                .strftime("%H:%M")
            )

        response = {
            "success": True,
            "tracking_code": booking.tracking_code,
            "booking_id": booking.id,
            "service_title": service.title,
            "duration_hours": duration_hours,
            "start_time": start_time,
            "end_time": end_time,
            "amount": int(booking.final_amount),
        }

        await _send_booking_push_safe(
            title="تغییر رزرو گرین ویتا",
            body=(
                f"{service.title} | "
                f"{start_time} تا {end_time} | "
                f"{customer_name} | "
                f"کد پیگیری: {booking.tracking_code}"
            ),
            url="/dashboard/",
            context={"booking_id": booking.id},
        )

        return response


@router.post("/api/cancel", include_in_schema=False)
async def cancel_booking(
    booking_id: int = Form(...),
):
    async with AsyncSessionLocal() as session:
        async with session.begin():

            booking_result = await session.execute(
                select(Booking)
                .where(Booking.id == booking_id)
                .with_for_update()
            )

            booking = booking_result.scalar_one_or_none()

            if booking is None:
                return {
                    "success": False,
                    "error": "رزرو موردنظر پیدا نشد.",
                }

            if booking.status == BookingStatus.CANCELLED:
                return {
                    "success": True,
                    "message": "این رزرو قبلاً لغو شده است.",
                }

            if booking.status in (
                BookingStatus.COMPLETED,
            ):
                return {
                    "success": False,
                    "error": "رزرو تکمیل‌شده قابل لغو نیست.",
                }

            assignment_result = await session.execute(
                select(BookingSlotAssignment)
                .where(
                    BookingSlotAssignment.booking_id
                    == booking.id
                )
                .with_for_update()
            )

            assignments = assignment_result.scalars().all()

            for assignment in assignments:
                slot = await session.get(
                    BookingTimeSlot,
                    assignment.time_slot_id,
                )

                if slot is not None:
                    slot.is_available = True

                await session.delete(assignment)

            booking.status = BookingStatus.CANCELLED

        response = {
            "success": True,
            "booking_id": booking.id,
            "tracking_code": booking.tracking_code,
            "status": booking.status,
            "released_slot_ids": [
                assignment.time_slot_id
                for assignment in assignments
            ],
        }

        await _send_booking_push_safe(
            title="لغو رزرو گرین ویتا",
            body=(
                f"{booking.customer_name} | "
                f"کد پیگیری: {booking.tracking_code} | "
                "رزرو لغو شد."
            ),
            url="/dashboard/",
            context={"booking_id": booking.id},
        )

        return response


@router.post("/api/book", include_in_schema=False)
async def create_booking(
    service_id: int = Form(...),
    slot_id: int = Form(...),
    duration_hours: int = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_email: str = Form(""),
    plant_name: str = Form(""),
    plant_description: str = Form(""),
    notes: str = Form(""),
):
    customer_name = customer_name.strip()
    customer_phone = customer_phone.strip()
    customer_email = customer_email.strip() or None
    plant_name = plant_name.strip() or None
    plant_description = (
        plant_description.strip()
        or None
    )
    notes = notes.strip() or None

    if not customer_name:
        return {
            "success": False,
            "error": "نام و نام خانوادگی الزامی است.",
        }

    if not customer_phone:
        return {
            "success": False,
            "error": "شماره تماس الزامی است.",
        }

    if (
        duration_hours < 1
        or duration_hours > MAX_BOOKING_DURATION_HOURS
    ):
        return {
            "success": False,
            "error": "مدت رزرو فقط بین ۱ تا ۳ ساعت مجاز است.",
        }

    async with AsyncSessionLocal() as session:
        async with session.begin():
            service = await session.get(
                Service,
                service_id,
            )

            if service is None or not service.is_active:
                return {
                    "success": False,
                    "error": "خدمت موردنظر پیدا نشد.",
                }

            max_duration_hours = (
                PHONE_CONSULTATION_MAX_DURATION_HOURS
                if service.id == PHONE_CONSULTATION_SERVICE_ID
                else MAX_BOOKING_DURATION_HOURS
            )

            buffer_hours = (
                PHONE_CONSULTATION_BUFFER_HOURS
                if service.id == PHONE_CONSULTATION_SERVICE_ID
                else BUFFER_HOURS
            )

            if duration_hours > max_duration_hours:
                return {
                    "success": False,
                    "error": (
                        "برای مشاوره تلفنی تخصصی فقط ۱ ساعت قابل رزرو است."
                        if service.id == PHONE_CONSULTATION_SERVICE_ID
                        else "مدت رزرو فقط بین ۱ تا ۳ ساعت مجاز است."
                    ),
                }

            start_result = await session.execute(
                select(BookingTimeSlot)
                .join(BookingSchedule)
                .where(
                    BookingTimeSlot.id == slot_id,
                    BookingSchedule.service_id == service_id,
                )
                .with_for_update()
            )

            start_slot = start_result.scalar_one_or_none()

            if start_slot is None:
                return {
                    "success": False,
                    "error": "زمان شروع پیدا نشد.",
                }

            now_tehran = datetime.now(TEHRAN)
            local_start = start_slot.starts_at.astimezone(TEHRAN)

            if (
                local_start.hour > MAX_BOOKING_START_HOUR
                or (
                    local_start.hour == MAX_BOOKING_START_HOUR
                    and local_start.minute > 0
                )
            ):
                return {
                    "success": False,
                    "error": "شروع رزرو حداکثر تا ساعت 17:00 مجاز است.",
                }

            if start_slot.starts_at <= now_tehran:
                return {
                    "success": False,
                    "error": "زمان انتخاب‌شده گذشته است.",
                }

            schedule = await session.get(
                BookingSchedule,
                start_slot.schedule_id,
            )

            if schedule is None:
                return {
                    "success": False,
                    "error": "برنامه زمانی پیدا نشد.",
                }

            total_slots = duration_hours + buffer_hours

            shared_end = (
                start_slot.starts_at
                + timedelta(hours=total_slots)
            )

            # قفل ظرفیت زمانی مشترک کل خدمات
            await session.execute(
                select(BookingTimeSlot.id)
                .where(
                    BookingTimeSlot.starts_at >= start_slot.starts_at,
                    BookingTimeSlot.starts_at < shared_end,
                )
                .with_for_update()
            )

            shared_occupied_starts = await get_shared_occupied_starts(
                session,
                start_slot.starts_at,
                shared_end,
            )

            if any(
                slot_start in shared_occupied_starts
                for slot_start in (
                    start_slot.starts_at
                    + timedelta(hours=i)
                    for i in range(total_slots)
                )
            ):
                return {
                    "success": False,
                    "error": (
                        "بخشی از این بازه یا دو ساعت بافر "
                        "توسط رزرو دیگری در یکی از خدمات اشغال شده است."
                    ),
                }

            result = await session.execute(
                select(BookingTimeSlot)
                .where(
                    BookingTimeSlot.schedule_id == schedule.id,
                    BookingTimeSlot.starts_at >= start_slot.starts_at,
                    BookingTimeSlot.starts_at
                    < start_slot.starts_at
                    + timedelta(hours=total_slots),
                )
                .order_by(BookingTimeSlot.starts_at)
                .with_for_update()
            )

            locked_slots = result.scalars().all()

            if len(locked_slots) != total_slots:
                return {
                    "success": False,
                    "error": (
                        "برای این مدت زمان، بازه کامل "
                        "و دو ساعت فاصله بعدی موجود نیست."
                    ),
                }

            for index in range(1, len(locked_slots)):
                previous = locked_slots[index - 1]
                current = locked_slots[index]

                if current.starts_at != previous.ends_at:
                    return {
                        "success": False,
                        "error": (
                            "ساعت‌های انتخاب‌شده باید کاملاً "
                            "متوالی باشند."
                        ),
                    }

            reserved_slots = locked_slots[:duration_hours]
            buffer_slots = locked_slots[duration_hours:]

            if not all(
                slot.is_available
                for slot in locked_slots
            ):
                return {
                    "success": False,
                    "error": (
                        "بخشی از این بازه یا دو ساعت بعد از آن "
                        "توسط رزرو دیگری اشغال شده است."
                    ),
                }

            base_amount = (
                Decimal(str(service.price or 0))
                * duration_hours
            )

            discount_amount = Decimal("0")
            final_amount = base_amount

            tracking_code = generate_tracking_code()

            existing = await session.execute(
                select(Booking.id).where(
                    Booking.tracking_code == tracking_code
                )
            )

            if existing.scalar_one_or_none() is not None:
                tracking_code = generate_tracking_code()

            booking = Booking(
                tracking_code=tracking_code,
                service_id=service.id,
                time_slot_id=start_slot.id,
                source=BookingSource.ONLINE,
                status=BookingStatus.PENDING,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                plant_name=plant_name,
                plant_description=plant_description,
                notes=notes,
                base_amount=base_amount,
                discount_amount=discount_amount,
                final_amount=final_amount,
            )

            session.add(booking)
            await session.flush()

            assignments = []

            for slot in reserved_slots:
                assignments.append(
                    BookingSlotAssignment(
                        booking_id=booking.id,
                        time_slot_id=slot.id,
                        kind="RESERVED",
                    )
                )
                slot.is_available = False

            for slot in buffer_slots:
                assignments.append(
                    BookingSlotAssignment(
                        booking_id=booking.id,
                        time_slot_id=slot.id,
                        kind="BUFFER",
                    )
                )
                slot.is_available = False

            session.add_all(assignments)

        end_time = (
            reserved_slots[-1].ends_at
            .astimezone(TEHRAN)
            .strftime("%H:%M")
        )

        start_time = (
            reserved_slots[0].starts_at
            .astimezone(TEHRAN)
            .strftime("%H:%M")
        )

        response = {
            "success": True,
            "tracking_code": tracking_code,
            "booking_id": booking.id,
            "service_title": service.title,
            "duration_hours": duration_hours,
            "start_time": start_time,
            "end_time": end_time,
            "amount": int(final_amount),
            "reserved_slot_ids": [
                slot.id
                for slot in reserved_slots
            ],
            "buffer_slot_ids": [
                slot.id
                for slot in buffer_slots
            ],
        }

        # Web Push برای پنل ادمین.
        # خطای اعلان نباید باعث شکست رزرو شود.
        try:
            async with AsyncSessionLocal() as push_session:
                await send_push(
                    push_session,
                    title="رزرو جدید گرین ویتا",
                    body=(
                        f"{service.title} | "
                        f"{start_time} تا {end_time} | "
                        f"{customer_name} | "
                        f"کد پیگیری: {tracking_code}"
                    ),
                    url="/dashboard/",
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "booking_admin_push_failed",
                extra={"booking_id": booking.id},
            )

        return response
