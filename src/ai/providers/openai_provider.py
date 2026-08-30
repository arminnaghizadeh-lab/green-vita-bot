"""OpenAI provider implementation."""

import base64

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ai.base import AIProvider, AIResponse, ChatMessage
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not api_key:
            raise AIProviderError("کلید API اوپن‌ای‌آی (OPENAI_API_KEY) تنظیم نشده است.")
        self.model = model
        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            # برای gatewayهای سازگار با OpenAI (مثل AvalAI/GapGPT) که از یک آدرس
            # غیر از api.openai.com سرو می‌شوند — مثلاً برای دسترسی به Claude از پشت آن‌ها.
            client_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**client_kwargs)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def chat(
        self, messages: list[ChatMessage], *, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            chat_messages = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.extend(
                {
                    "role": (
                        m.role.value
                        if hasattr(m.role, "value")
                        else str(m.role)
                    ),
                    "content": m.content,
                }
                for m in messages
            )

            response = await self.client.with_options(
                max_retries=0, timeout=90.0
            ).chat.completions.create(
                model=self.model,
                messages=chat_messages,
                reasoning_effort="low",
                max_tokens=4096,
            )
            text = response.choices[0].message.content or ""
            return AIResponse(text=text, provider=self.name, model=self.model)
        except Exception as exc:  # noqa: BLE001
            logger.error("openai_chat_failed", error=str(exc))
            raise AIProviderError("خطا در ارتباط با OpenAI.") from exc

    async def analyze_image(
        self, image_bytes: bytes, *, prompt: str, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            chat_messages = []
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                }
            )
            response = await self.client.with_options(
                max_retries=0,
                timeout=90.0,
            ).chat.completions.create(
                model=self.model,
                messages=chat_messages,
                max_tokens=1024,
            )
            text = response.choices[0].message.content or ""
            return AIResponse(text=text, provider=self.name, model=self.model)
        except Exception as exc:  # noqa: BLE001
            status_code = getattr(exc, "status_code", None)
            error_body = getattr(exc, "body", None)

            if status_code == 429:
                logger.error(
                    "openai_image_analysis_quota_or_rate_limit",
                    status_code=status_code,
                    error=error_body or str(exc),
                )
                raise AIProviderError(
                    "اعتبار سرویس تحلیل تصویر کافی نیست یا محدودیت درخواست فعال شده است. لطفاً بعداً دوباره تلاش کنید."
                ) from exc

            if status_code == 504:
                logger.error(
                    "openai_image_analysis_gateway_timeout",
                    status_code=status_code,
                    error=error_body or str(exc),
                )
                raise AIProviderError(
                    "سرویس تحلیل تصویر موقتاً پاسخ نمی‌دهد. لطفاً چند لحظه بعد دوباره تلاش کنید."
                ) from exc

            logger.error(
                "openai_image_analysis_failed",
                status_code=status_code,
                error=error_body or str(exc),
            )
            raise AIProviderError("خطا در تحلیل تصویر با OpenAI.") from exc
