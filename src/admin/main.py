import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import mimetypes
mimetypes.add_type("image/webp", ".webp")

from fastapi import FastAPI, Request
from sqlalchemy import func, select
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.admin.auth import SESSION_KEY
from src.admin.routers import auth, booking, dashboard, diagnosis_online, public, push, smart_bio, visits
from src.core.config import get_settings
from src.db.session import AsyncSessionLocal
from src.db.models.booking import BookingTimeSlot
from src.services.booking_slots import generate_slots_for_range

app = FastAPI(
    title="Green Vita Admin",
    docs_url=None,
    redoc_url=None,
)

settings = get_settings()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret or settings.secret_key,
)


app.mount(
    "/static",
    StaticFiles(directory="src/admin/static"),
    name="static",
)

@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    from fastapi.responses import FileResponse
    return FileResponse(
        "src/admin/static/sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )






# ============================================================
# GV_BOOKING_SLOT_DAILY_JOB
# Keep booking slots available for the next 30 days.
# Runs once at startup, then every 24 hours.
# Existing slots are never deleted or duplicated.
# ============================================================

TEHRAN = ZoneInfo("Asia/Tehran")
BOOKING_HORIZON_DAYS = 30
BOOKING_SLOT_CHECK_INTERVAL = 24 * 60 * 60

_booking_slot_task = None


async def ensure_booking_slot_horizon():
    try:
        now = datetime.now(TEHRAN)
        horizon_date = now.date() + timedelta(days=BOOKING_HORIZON_DAYS)

        async with AsyncSessionLocal() as session:
            max_start = await session.scalar(
                select(func.max(BookingTimeSlot.starts_at))
            )

            if max_start is None:
                start_date = now.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            else:
                max_local = max_start.astimezone(TEHRAN)
                start_date = datetime.combine(
                    max_local.date() + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=TEHRAN,
                )

            if start_date.date() <= horizon_date:
                days = (horizon_date - start_date.date()).days + 1

                created = await generate_slots_for_range(
                    session,
                    start_date,
                    days,
                )

                print(
                    f"[booking] daily horizon update: "
                    f"created={created}, "
                    f"through={horizon_date.isoformat()}",
                    flush=True,
                )
            else:
                print(
                    f"[booking] daily horizon already sufficient: "
                    f"through={max_start.astimezone(TEHRAN).date().isoformat()}",
                    flush=True,
                )

    except Exception as exc:
        print(
            f"[booking] daily horizon update failed: {exc!r}",
            flush=True,
        )


async def booking_slot_daily_loop():
    await ensure_booking_slot_horizon()

    while True:
        await asyncio.sleep(BOOKING_SLOT_CHECK_INTERVAL)
        await ensure_booking_slot_horizon()


@app.on_event("startup")
async def start_booking_slot_daily_job():
    global _booking_slot_task

    if _booking_slot_task is None or _booking_slot_task.done():
        _booking_slot_task = asyncio.create_task(
            booking_slot_daily_loop()
        )

        print(
            "[booking] daily slot job started; interval=24h",
            flush=True,
        )


@app.on_event("shutdown")
async def stop_booking_slot_daily_job():
    global _booking_slot_task

    if _booking_slot_task is not None:
        _booking_slot_task.cancel()

        try:
            await _booking_slot_task
        except asyncio.CancelledError:
            pass

        _booking_slot_task = None

app.include_router(auth.router)
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(visits.router)
app.include_router(smart_bio.router)
app.include_router(push.router)
app.include_router(booking.router)
app.include_router(public.router)
app.include_router(diagnosis_online.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


