"""Claude (Anthropic) provider implementation."""

import base64

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.ai.base import AIProvider, AIResponse, ChatMessage
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger

logger = get_logger(__name__)


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise AIProviderError("کلید API کلود (ANTHROPIC_API_KEY) تنظیم نشده است.")
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def chat(
        self, messages: list[ChatMessage], *, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt or "",
                messages=[{"role": m.role.value, "content": m.content} for m in messages],
            )
            text = "".join(block.text for block in response.content if block.type == "text")
            return AIResponse(text=text, provider=self.name, model=self.model)
        except Exception as exc:  # noqa: BLE001
            logger.error("claude_chat_failed", error=str(exc))
            raise AIProviderError("خطا در ارتباط با Claude.") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def analyze_image(
        self, image_bytes: bytes, *, prompt: str, system_prompt: str | None = None
    ) -> AIResponse:
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt or "",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": b64_image,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            text = "".join(block.text for block in response.content if block.type == "text")
            return AIResponse(text=text, provider=self.name, model=self.model)
        except Exception as exc:  # noqa: BLE001
            logger.error("claude_image_analysis_failed", error=str(exc))
            raise AIProviderError("خطا در تحلیل تصویر با Claude.") from exc
