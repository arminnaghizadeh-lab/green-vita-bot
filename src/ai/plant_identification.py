"""
Plant species identification service.

مشابه src/ai/diagnosis.py، اما به‌جای تشخیص بیماری، گونه‌ی گیاه و راهنمای کامل
نگهداری آن را از روی عکس استخراج می‌کند. خروجی مدل هم اینجا اجباراً JSON است
تا هم در پیام تلگرام فرمت شود و هم به‌صورت ساختاریافته در دیتابیس ذخیره شود.
"""

import json
import re
from dataclasses import dataclass, field

from src.ai.base import AIProvider
from src.core.logging import get_logger
from src.db.models.plant_identification import DifficultyLevel

logger = get_logger("ai.plant_identification")

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_VALID_DIFFICULTIES = {d.value for d in DifficultyLevel}

PLANT_ID_SYSTEM_PROMPT = """
تو یک گیاه‌شناس و متخصص باتجربه در کلینیک گیاه‌پزشکی «گرین‌ویتا» هستی.
کاربر عکسی از یک گیاه فرستاده و می‌خواهد بدونه این گیاه چیه و چطور باید ازش نگهداری کنه.

قوانین پاسخ‌دهی:
1. فقط و فقط یک شیء JSON معتبر برگردان — بدون ```json، بدون توضیح اضافه، بدون متن قبل یا بعد از آن.
2. اگر عکس گیاه نبود یا برای شناسایی کافی نبود، is_plant را false بگذار، persian_name را
   "تصویر نامشخص یا نامرتبط" بگذار و در preventive_care_tips از کاربر بخواه عکس واضح‌تری بفرستد.
3. اگر مطمئن نیستی دقیقاً چه گونه‌ای است، نزدیک‌ترین حدس معقول را بزن و confidence را پایین بگذار
   — هرگز فیلدها را خالی نگذار یا حدس نزن که "نمی‌دانم".
4. همه‌ی مقادیر متنی باید فارسی، ساده، کاربردی و مختص همین گیاه باشند (نه توصیه‌ی کلی گیاهان).
5. راهنمای نگهداری باید عملی و قابل‌اجرا برای یک علاقمند غیرحرفه‌ای به گل و گیاه باشد.

ساختار دقیق JSON خروجی:
{
  "is_plant": true یا false,
  "persian_name": "نام فارسی/رایج گیاه",
  "scientific_name": "نام علمی به لاتین",
  "confidence": عددی بین 0 تا 100,
  "difficulty_level": "easy" یا "medium" یا "hard",
  "light_requirement": "نیاز نوری به فارسی",
  "watering_schedule": "برنامه آبیاری به فارسی",
  "humidity": "رطوبت مناسب به فارسی",
  "temperature": "دمای مناسب به فارسی",
  "soil_mix": "ترکیب خاک مناسب به فارسی",
  "fertilizer_recommendation": "توصیه کوددهی به فارسی",
  "potting_advice": "توصیه گلدان و کاشت به فارسی",
  "repotting_interval": "فاصله زمانی تعویض گلدان به فارسی",
  "propagation_methods": ["روش تکثیر اول", "روش تکثیر دوم"],
  "common_pests": ["آفت رایج اول", "آفت رایج دوم"],
  "common_diseases": ["بیماری رایج اول", "بیماری رایج دوم"],
  "toxicity_pets": "سمیت برای حیوانات خانگی به فارسی",
  "toxicity_humans": "سمیت برای انسان به فارسی",
  "preventive_care_tips": "نکات پیشگیرانه نگهداری به فارسی"
}
""".strip()


def build_plant_id_user_prompt() -> str:
    return "لطفاً طبق قالب JSON مشخص‌شده در دستورالعمل سیستم، این گیاه را از روی عکس شناسایی و راهنمای نگهداری آن را ارائه کن."


@dataclass
class PlantIdentificationResult:
    is_plant: bool
    persian_name: str
    scientific_name: str
    confidence: int
    difficulty_level: DifficultyLevel
    light_requirement: str = ""
    watering_schedule: str = ""
    humidity: str = ""
    temperature: str = ""
    soil_mix: str = ""
    fertilizer_recommendation: str = ""
    potting_advice: str = ""
    repotting_interval: str = ""
    propagation_methods: list[str] = field(default_factory=list)
    common_pests: list[str] = field(default_factory=list)
    common_diseases: list[str] = field(default_factory=list)
    toxicity_pets: str = ""
    toxicity_humans: str = ""
    preventive_care_tips: str = ""
    ai_provider: str = ""
    raw_response: str = ""
    parse_succeeded: bool = True


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip()).strip()


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def parse_plant_identification_response(
    raw_text: str, *, ai_provider: str
) -> PlantIdentificationResult:
    """متن خام مدل را به PlantIdentificationResult تبدیل می‌کند؛ با fallback امن در صورت خطا."""
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)

        difficulty_raw = str(data.get("difficulty_level", "unknown")).lower()
        difficulty = (
            DifficultyLevel(difficulty_raw)
            if difficulty_raw in _VALID_DIFFICULTIES
            else DifficultyLevel.UNKNOWN
        )

        confidence = max(0, min(100, int(data.get("confidence", 0))))

        return PlantIdentificationResult(
            is_plant=bool(data.get("is_plant", True)),
            persian_name=str(data.get("persian_name", "نامشخص")),
            scientific_name=str(data.get("scientific_name", "")),
            confidence=confidence,
            difficulty_level=difficulty,
            light_requirement=str(data.get("light_requirement", "")),
            watering_schedule=str(data.get("watering_schedule", "")),
            humidity=str(data.get("humidity", "")),
            temperature=str(data.get("temperature", "")),
            soil_mix=str(data.get("soil_mix", "")),
            fertilizer_recommendation=str(data.get("fertilizer_recommendation", "")),
            potting_advice=str(data.get("potting_advice", "")),
            repotting_interval=str(data.get("repotting_interval", "")),
            propagation_methods=_as_list(data.get("propagation_methods")),
            common_pests=_as_list(data.get("common_pests")),
            common_diseases=_as_list(data.get("common_diseases")),
            toxicity_pets=str(data.get("toxicity_pets", "")),
            toxicity_humans=str(data.get("toxicity_humans", "")),
            preventive_care_tips=str(data.get("preventive_care_tips", "")),
            ai_provider=ai_provider,
            raw_response=raw_text,
            parse_succeeded=True,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("plant_id_parse_failed", error=str(exc), raw_preview=raw_text[:200])
        return PlantIdentificationResult(
            is_plant=False,
            persian_name="نامشخص",
            scientific_name="",
            confidence=0,
            difficulty_level=DifficultyLevel.UNKNOWN,
            preventive_care_tips=raw_text.strip() or "پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.",
            ai_provider=ai_provider,
            raw_response=raw_text,
            parse_succeeded=False,
        )


async def identify_plant_image(
    ai_provider: AIProvider, image_bytes: bytes
) -> PlantIdentificationResult:
    """نقطه‌ی ورود اصلی: عکس خام را می‌گیرد و نتیجه‌ی شناسایی ساختاریافته برمی‌گرداند."""
    response = await ai_provider.analyze_image(
        image_bytes,
        prompt=build_plant_id_user_prompt(),
        system_prompt=PLANT_ID_SYSTEM_PROMPT,
    )
    return parse_plant_identification_response(response.text, ai_provider=response.provider)
