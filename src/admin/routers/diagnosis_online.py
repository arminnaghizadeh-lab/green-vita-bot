from __future__ import annotations

import hashlib
import ipaddress
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.db.models.web_account import WebAccount, WebDiagnosisUsage
from src.db.session import AsyncSessionLocal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates

from src.ai.diagnosis import diagnose_plant_image
from src.ai.factory import get_ai_provider
from src.ai.plant_identification import identify_plant_image
from src.core.logging import get_logger

router = APIRouter(tags=["online-plant-diagnosis"])
templates = Jinja2Templates(directory="src/admin/templates")
logger = get_logger("admin.online_plant_diagnosis")

MAX_IMAGE_BYTES = 8 * 1024 * 1024
RATE_WINDOW_SECONDS = 60
RATE_HOUR_SECONDS = 3600
RATE_PER_MINUTE = 4
RATE_PER_HOUR = 15
_request_times: dict[str, deque[float]] = {}


def _client_ip(request: Request) -> str:
    # X-Real-IP باید توسط reverse proxy به IP واقعی کاربر تنظیم شود.
    candidate = request.headers.get("x-real-ip", "").strip()
    if not candidate and request.client:
        candidate = request.client.host
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return "unknown"


def _check_rate_limit(request: Request) -> None:
    now = time.monotonic()
    key = _client_ip(request)
    bucket = _request_times.setdefault(key, deque())

    while bucket and now - bucket[0] >= RATE_HOUR_SECONDS:
        bucket.popleft()

    requests_last_minute = sum(
        1 for timestamp in bucket
        if now - timestamp < RATE_WINDOW_SECONDS
    )

    if (
        requests_last_minute >= RATE_PER_MINUTE
        or len(bucket) >= RATE_PER_HOUR
    ):
        raise HTTPException(
            status_code=429,
            detail="تعداد درخواست‌ها زیاد است؛ کمی بعد دوباره امتحان کن.",
            headers={"Retry-After": "60"},
        )

    bucket.append(now)

    # جلوگیری از رشد نامحدود حافظه در صورت تعداد زیاد IP.
    if len(_request_times) > 5000:
        stale_keys = [
            ip for ip, times in _request_times.items()
            if not times or now - times[-1] >= RATE_HOUR_SECONDS
        ]
        for ip in stale_keys:
            _request_times.pop(ip, None)




TEHRAN = ZoneInfo("Asia/Tehran")


async def _reserve_daily_usage(
    *,
    account_id: int,
    mode: str,
    plant_name: str,
    notes: str,
    image_filename: str | None,
    image_sha256: str,
) -> int:
    """Reserve one diagnosis for this account and Tehran calendar day."""
    now = datetime.now(timezone.utc)
    today = now.astimezone(TEHRAN).date()

    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(WebAccount)
            .where(
                WebAccount.id == account_id,
                WebAccount.is_active.is_(True),
            )
            .with_for_update()
        )
        if account is None:
            raise HTTPException(
                status_code=401,
                detail="حساب کاربری فعال پیدا نشد؛ دوباره وارد حساب شو.",
            )

        existing = await session.scalar(
            select(WebDiagnosisUsage).where(
                WebDiagnosisUsage.account_id == account_id,
                WebDiagnosisUsage.usage_date == today,
            )
        )

        if existing is not None:
            stale = False
            if existing.status == "processing" and existing.created_at:
                created = existing.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                stale = now - created > timedelta(minutes=10)

            if existing.status == "failed" or stale:
                await session.delete(existing)
                await session.flush()
            elif existing.status == "processing":
                raise HTTPException(
                    status_code=429,
                    detail="درخواست تشخیص امروز هنوز در حال پردازش است؛ کمی بعد دوباره بررسی کن.",
                    headers={"Retry-After": "60"},
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail="سهمیه تشخیص آنلاین امروز استفاده شده است. فردا دوباره مراجعه کن.",
                )

        usage = WebDiagnosisUsage(
            account_id=account_id,
            usage_date=today,
            mode=mode,
            plant_name=plant_name or None,
            notes=notes or None,
            image_filename=image_filename,
            image_sha256=image_sha256,
            status="processing",
        )
        session.add(usage)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=429,
                detail="سهمیه تشخیص آنلاین امروز استفاده شده است. فردا دوباره مراجعه کن.",
            ) from None

        return usage.id


async def _remove_failed_usage(usage_id: int) -> None:
    """Free the daily quota when analysis fails."""
    try:
        async with AsyncSessionLocal() as session:
            usage = await session.get(WebDiagnosisUsage, usage_id)
            if usage is not None and usage.status == "processing":
                await session.delete(usage)
                await session.commit()
    except Exception as exc:
        logger.error(
            "web_plant_analysis_usage_cleanup_failed",
            error_type=type(exc).__name__,
        )


@router.get("/diagnosis/", include_in_schema=False)
async def diagnosis_page(request: Request):
    return templates.TemplateResponse(
        "public/diagnosis.html",
        {"request": request},
    )


@router.post("/diagnosis/api/analyze")
async def analyze_plant_online(
    request: Request,
    mode: str = Form(...),
    image: UploadFile = File(...),
    plant_name: str = Form(""),
    notes: str = Form(""),
):
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        raise HTTPException(
            status_code=403,
            detail="درخواست معتبر نیست؛ صفحه را تازه‌سازی و دوباره تلاش کن.",
        )

    if mode not in {"diagnose", "identify"}:
        raise HTTPException(status_code=400, detail="نوع درخواست معتبر نیست.")

    try:
        account_id = int(request.session.get("web_account_id"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="برای استفاده از تشخیص آنلاین ابتدا از بخش حساب کاربری وارد شو.",
        ) from None

    plant_name = plant_name.strip()
    notes = notes.strip()

    if len(plant_name) > 120:
        raise HTTPException(status_code=400, detail="نام گیاه بیش از حد طولانی است.")
    if len(notes) > 1500:
        raise HTTPException(status_code=400, detail="توضیحات بیش از حد طولانی است.")

    _check_rate_limit(request)
    usage_id: int | None = None

    try:
        if image.content_type != "image/jpeg":
            raise HTTPException(
                status_code=415,
                detail="عکس باید از طریق فرم سایت بارگذاری شود تا به قالب مناسب تبدیل شود.",
            )

        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="حجم عکس پس از فشرده‌سازی باید کمتر از ۸ مگابایت باشد.",
            )

        # رابط سایت تصاویر را به JPEG تبدیل می‌کند؛ این بررسی، ورودی جعلی
        # یا فایلی با نوع نامعتبر را پیش از فراخوانی سرویس AI رد می‌کند.
        if (
            len(image_bytes) < 100
            or not image_bytes.startswith(b"\xff\xd8\xff")
            or not image_bytes.endswith(b"\xff\xd9")
        ):
            raise HTTPException(
                status_code=415,
                detail="فایل عکس معتبر نیست؛ لطفاً تصویر دیگری انتخاب کن.",
            )

        safe_filename = (
            str(image.filename or "")
            .replace("\\", "/")
            .rsplit("/", 1)[-1][:255]
            or None
        )

        usage_id = await _reserve_daily_usage(
            account_id=account_id,
            mode=mode,
            plant_name=plant_name,
            notes=notes,
            image_filename=safe_filename,
            image_sha256=hashlib.sha256(image_bytes).hexdigest(),
        )

        provider = get_ai_provider()

        if mode == "diagnose":
            result = await diagnose_plant_image(
                provider,
                image_bytes,
                plant_name=plant_name or None,
                user_notes=notes or None,
            )
            payload = {
                "is_healthy": result.is_healthy,
                "disease_name": result.disease_name,
                "severity": result.severity.value,
                "confidence": result.confidence,
                "symptoms": result.symptoms,
                "cause": result.cause,
                "treatment": result.treatment,
                "prevention": result.prevention,
                "parse_succeeded": result.parse_succeeded,
            }
        else:
            result = await identify_plant_image(provider, image_bytes)
            payload = {
                "is_plant": result.is_plant,
                "persian_name": result.persian_name,
                "scientific_name": result.scientific_name,
                "confidence": result.confidence,
                "difficulty_level": result.difficulty_level.value,
                "light_requirement": result.light_requirement,
                "watering_schedule": result.watering_schedule,
                "humidity": result.humidity,
                "temperature": result.temperature,
                "soil_mix": result.soil_mix,
                "fertilizer_recommendation": result.fertilizer_recommendation,
                "potting_advice": result.potting_advice,
                "repotting_interval": result.repotting_interval,
                "propagation_methods": result.propagation_methods,
                "common_pests": result.common_pests,
                "common_diseases": result.common_diseases,
                "toxicity_pets": result.toxicity_pets,
                "toxicity_humans": result.toxicity_humans,
                "preventive_care_tips": result.preventive_care_tips,
                "parse_succeeded": result.parse_succeeded,
            }

        async with AsyncSessionLocal() as session:
            usage = await session.get(WebDiagnosisUsage, usage_id)
            if usage is None:
                raise RuntimeError("Diagnosis usage reservation was not found")
            usage.result = payload
            usage.status = "completed"
            usage.ai_provider = type(provider).__name__[:32]
            await session.commit()

        return {"ok": True, "mode": mode, "result": payload}

    except HTTPException:
        if usage_id is not None:
            await _remove_failed_usage(usage_id)
        raise
    except Exception as exc:
        if usage_id is not None:
            await _remove_failed_usage(usage_id)
        # جزئیات داخلی و اطلاعات محرمانه به مرورگر ارسال نمی‌شوند.
        logger.error(
            "web_plant_analysis_failed",
            mode=mode,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="در حال حاضر تحلیل تصویر انجام نشد. کمی بعد دوباره تلاش کن.",
        ) from exc
    finally:
        await image.close()
