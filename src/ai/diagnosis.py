"""
Disease diagnosis service.

این ماژول لایه‌ی هوش مصنوعی خام (AIProvider.analyze_image) را به یک نتیجه‌ی
ساختاریافته و قابل‌اعتماد (DiagnosisResult) تبدیل می‌کند. هندلر بات فقط با
diagnose_plant_image کار می‌کند و اصلاً نمی‌داند پشت صحنه Claude است یا Gemini
یا OpenAI، و اصلاً نمی‌داند پارس JSON چطور انجام می‌شود.
"""

import json
import re
from dataclasses import dataclass, field

from src.ai.base import AIProvider
from src.ai.prompts import DIAGNOSIS_SYSTEM_PROMPT, build_diagnosis_user_prompt
from src.core.logging import get_logger
from src.db.models.diagnosis import DiagnosisSeverity

logger = get_logger("ai.diagnosis")

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_VALID_SEVERITIES = {s.value for s in DiagnosisSeverity}


@dataclass
class DiagnosisResult:
    is_healthy: bool
    disease_name: str
    severity: DiagnosisSeverity
    confidence: int
    symptoms: list[str] = field(default_factory=list)
    cause: str = ""
    treatment: str = ""
    prevention: str = ""
    ai_provider: str = ""
    raw_response: str = ""
    parse_succeeded: bool = True


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip()).strip()


def parse_diagnosis_response(raw_text: str, *, ai_provider: str) -> DiagnosisResult:
    """
    متن خام مدل را به DiagnosisResult تبدیل می‌کند.

    اگر پارس JSON شکست بخورد، به‌جای کرش کردن، یک نتیجه‌ی fallback معتبر
    برمی‌گرداند (parse_succeeded=False) تا کاربر همچنان پاسخی دریافت کند.
    """
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)

        severity_raw = str(data.get("severity", "unknown")).lower()
        severity = (
            DiagnosisSeverity(severity_raw)
            if severity_raw in _VALID_SEVERITIES
            else DiagnosisSeverity.UNKNOWN
        )

        confidence = int(data.get("confidence", 0))
        confidence = max(0, min(100, confidence))

        symptoms = data.get("symptoms", [])
        if not isinstance(symptoms, list):
            symptoms = [str(symptoms)]

        return DiagnosisResult(
            is_healthy=bool(data.get("is_healthy", False)),
            disease_name=str(data.get("disease_name", "نامشخص")),
            severity=severity,
            confidence=confidence,
            symptoms=[str(s) for s in symptoms],
            cause=str(data.get("cause", "")),
            treatment=str(data.get("treatment", "")),
            prevention=str(data.get("prevention", "")),
            ai_provider=ai_provider,
            raw_response=raw_text,
            parse_succeeded=True,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("diagnosis_parse_failed", error=str(exc), raw_preview=raw_text[:200])
        return DiagnosisResult(
            is_healthy=False,
            disease_name="نامشخص",
            severity=DiagnosisSeverity.UNKNOWN,
            confidence=0,
            symptoms=[],
            treatment=raw_text.strip() or "پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.",
            prevention="",
            ai_provider=ai_provider,
            raw_response=raw_text,
            parse_succeeded=False,
        )


async def diagnose_plant_image(
    ai_provider: AIProvider,
    image_bytes: bytes,
    *,
    plant_name: str | None = None,
    user_notes: str | None = None,
) -> DiagnosisResult:
    """نقطه‌ی ورود اصلی: عکس خام را می‌گیرد و نتیجه‌ی تشخیص ساختاریافته برمی‌گرداند."""
    response = await ai_provider.analyze_image(
        image_bytes,
        prompt=build_diagnosis_user_prompt(plant_name, user_notes),
        system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
    )
    return parse_diagnosis_response(response.text, ai_provider=response.provider)
