from __future__ import annotations

import ipaddress
import time
from collections import deque

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

    plant_name = plant_name.strip()
    notes = notes.strip()

    if len(plant_name) > 120:
        raise HTTPException(status_code=400, detail="نام گیاه بیش از حد طولانی است.")
    if len(notes) > 1500:
        raise HTTPException(status_code=400, detail="توضیحات بیش از حد طولانی است.")

    _check_rate_limit(request)

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

        return {"ok": True, "mode": mode, "result": payload}

    except HTTPException:
        raise
    except Exception as exc:
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
