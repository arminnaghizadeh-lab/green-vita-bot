"""Gemini (Google) provider implementation."""

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ai.base import AIProvider, AIResponse, ChatMessage
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger

logger = get_logger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise AIProviderError("کلید API جمینای (GEMINI_API_KEY) تنظیم نشده است.")
        genai.configure(api_key=api_key)
        self.model_name = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def chat(
        self, messages: list[ChatMessage], *, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt or None,
            )
            history = [{"role": m.role.value, "parts": [m.content]} for m in messages[:-1]]
            chat_session = model.start_chat(history=history)
            last_message = messages[-1].content if messages else ""
            result = await chat_session.send_message_async(last_message)
            return AIResponse(text=result.text, provider=self.name, model=self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_chat_failed", error=str(exc))
            raise AIProviderError("خطا در ارتباط با Gemini.") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def analyze_image(
        self, image_bytes: bytes, *, prompt: str, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt or None,
            )
            image_part = {"mime_type": "image/jpeg", "data": image_bytes}
            result = await model.generate_content_async([prompt, image_part])
            return AIResponse(text=result.text, provider=self.name, model=self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("gemini_image_analysis_failed", error=str(exc))
            raise AIProviderError("خطا در تحلیل تصویر با Gemini.") from exc
