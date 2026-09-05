from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from src.db.models.booking import BookingSchedule, BookingTimeSlot, Service
from src.db.session import AsyncSessionLocal

router = APIRouter(prefix="/booking", tags=["booking"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
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


@router.get("/service/{service_id}/", response_class=HTMLResponse, include_in_schema=False)
async def booking_service(request: Request, service_id: int):
    async with AsyncSessionLocal() as session:
        service = await session.get(Service, service_id)

    if service is None or not service.is_active:
        return HTMLResponse("خدمت موردنظر پیدا نشد.", status_code=404)

    return templates.TemplateResponse(
        "booking/service.html",
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


@router.get("/api/slots/{service_id}/{jalali_date}", include_in_schema=False)
async def booking_slots(service_id: int, jalali_date: str):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    import jdatetime

    tehran = ZoneInfo("Asia/Tehran")

    try:
        jy, jm, jd = map(int, jalali_date.split("-"))
        start_j = jdatetime.datetime(jy, jm, jd, tzinfo=tehran)
        start_g = start_j.togregorian()
        end_g = start_g + timedelta(days=1)
    except (ValueError, TypeError):
        return {"error": "تاریخ نامعتبر است."}

    async with AsyncSessionLocal() as session:
        service = await session.get(Service, service_id)
        if service is None or not service.is_active:
            return {"error": "خدمت موردنظر پیدا نشد."}

        result = await session.execute(
            select(BookingTimeSlot)
            .join(BookingSchedule)
            .where(
                BookingSchedule.service_id == service_id,
                BookingTimeSlot.starts_at >= start_g,
                BookingTimeSlot.starts_at < end_g,
                BookingTimeSlot.is_available.is_(True),
            )
            .order_by(BookingTimeSlot.starts_at)
        )
        slots = result.scalars().all()

        output = []
        for slot in slots:
            local_start = slot.starts_at.astimezone(tehran)
            output.append(
                {
                    "id": slot.id,
                    "date": local_start.strftime("%Y-%m-%d"),
                    "time": local_start.strftime("%H:%M"),
                    "starts_at": local_start.isoformat(),
                }
            )

    return {
        "service_id": service_id,
        "date": jalali_date,
        "slots": output,
    }
