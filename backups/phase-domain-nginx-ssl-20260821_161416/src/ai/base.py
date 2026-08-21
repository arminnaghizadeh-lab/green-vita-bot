"""
AI Provider abstraction.

هر پروایدر (Claude / Gemini / OpenAI) باید این اینترفیس را پیاده‌سازی کند.
بقیه‌ی برنامه (هندلرهای بات، سرویس‌ها) فقط با AIProvider کار می‌کنند و
هیچ‌وقت مستقیم به SDK یک شرکت خاص وابسته نیستند — همین چیزی است که
سوییچ‌کردن پروایدر را با یک متغیر محیطی ممکن می‌کند.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: ChatRole
    content: str


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """قرارداد مشترکی که هر پروایدر هوش مصنوعی باید رعایت کند."""

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system_prompt: str | None = None,
    ) -> AIResponse:
        """یک پیام متنی می‌فرستد و پاسخ متنی برمی‌گرداند."""
        raise NotImplementedError

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        *,
        prompt: str,
        system_prompt: str | None = None,
    ) -> AIResponse:
        """
        تحلیل تصویر (مثلاً برای تشخیص بیماری گیاه در فازهای بعدی).
        در فاز ۱ فقط امضای متد تعریف می‌شود و پیاده‌سازی واقعی در فاز
        تشخیص بیماری تکمیل خواهد شد.
        """
        raise NotImplementedError
