"""تست‌های src.ai.diagnosis و src.ai.prompts"""

from src.ai.diagnosis import parse_diagnosis_response
from src.ai.prompts import build_diagnosis_user_prompt
from src.db.models.diagnosis import DiagnosisSeverity


def test_parse_diagnosis_response_valid_json():
    raw = """{
        "is_healthy": false,
        "disease_name": "لکه برگی قارچی",
        "severity": "moderate",
        "confidence": 78,
        "symptoms": ["لکه‌های قهوه‌ای روی برگ", "زردی اطراف لکه‌ها"],
        "cause": "رطوبت زیاد روی برگ‌ها و تهویه ضعیف",
        "treatment": "برگ‌های آلوده را حذف کن و قارچ‌کش مناسب استفاده کن.",
        "prevention": "آبیاری از بالای برگ را کاهش بده."
    }"""

    result = parse_diagnosis_response(raw, ai_provider="claude")

    assert result.parse_succeeded is True
    assert result.is_healthy is False
    assert result.disease_name == "لکه برگی قارچی"
    assert result.severity == DiagnosisSeverity.MODERATE
    assert result.confidence == 78
    assert len(result.symptoms) == 2
    assert result.cause == "رطوبت زیاد روی برگ‌ها و تهویه ضعیف"
    assert result.ai_provider == "claude"


def test_parse_diagnosis_response_missing_cause_defaults_to_empty_string():
    raw = '{"is_healthy": false, "disease_name": "x", "severity": "mild", "confidence": 50, "symptoms": [], "treatment": "t", "prevention": "p"}'

    result = parse_diagnosis_response(raw, ai_provider="claude")

    assert result.cause == ""


def test_parse_diagnosis_response_strips_code_fences():
    raw = '```json\n{"is_healthy": true, "disease_name": "سالم", "severity": "none", "confidence": 95, "symptoms": [], "treatment": "", "prevention": ""}\n```'

    result = parse_diagnosis_response(raw, ai_provider="gemini")

    assert result.parse_succeeded is True
    assert result.is_healthy is True
    assert result.severity == DiagnosisSeverity.NONE


def test_parse_diagnosis_response_clamps_confidence_range():
    raw = '{"is_healthy": false, "disease_name": "x", "severity": "mild", "confidence": 250, "symptoms": [], "treatment": "", "prevention": ""}'

    result = parse_diagnosis_response(raw, ai_provider="openai")

    assert result.confidence == 100


def test_parse_diagnosis_response_invalid_severity_falls_back_to_unknown():
    raw = '{"is_healthy": false, "disease_name": "x", "severity": "catastrophic", "confidence": 10, "symptoms": [], "treatment": "", "prevention": ""}'

    result = parse_diagnosis_response(raw, ai_provider="claude")

    assert result.severity == DiagnosisSeverity.UNKNOWN


def test_parse_diagnosis_response_invalid_json_returns_fallback():
    raw = "متاسفم، نمی‌تونم این عکس رو تحلیل کنم."

    result = parse_diagnosis_response(raw, ai_provider="claude")

    assert result.parse_succeeded is False
    assert result.disease_name == "نامشخص"
    assert result.treatment == raw


def test_build_diagnosis_user_prompt_with_name_and_notes():
    prompt = build_diagnosis_user_prompt("مونستِرا", "برگ‌هاش زرد شدن")

    assert "مونستِرا" in prompt
    assert "برگ‌هاش زرد شدن" in prompt


def test_build_diagnosis_user_prompt_without_name():
    prompt = build_diagnosis_user_prompt(None, None)

    assert "نمی‌داند" in prompt
