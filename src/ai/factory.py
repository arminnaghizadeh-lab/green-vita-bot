"""
AI Provider factory.

نقطه‌ی واحدی که بر اساس AI_PROVIDER در .env، پروایدر مناسب را می‌سازد.
تغییر پروایدر یعنی فقط عوض‌کردن یک خط در .env — هیچ کد دیگری دست نمی‌خورد.
"""

from functools import lru_cache

from src.ai.base import AIProvider
from src.ai.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.core.config import Settings, get_settings
from src.core.exceptions import ConfigurationError


def build_ai_provider(settings: Settings) -> AIProvider:
    provider_map = {
        "claude": lambda: ClaudeProvider(
            api_key=settings.anthropic_api_key, model=settings.anthropic_model
        ),
        "gemini": lambda: GeminiProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_model
        ),
        "openai": lambda: OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url or None,
        ),
    }

    builder = provider_map.get(settings.ai_provider)
    if builder is None:
        raise ConfigurationError(
            f"AI_PROVIDER نامعتبر است: {settings.ai_provider!r}. "
            f"مقادیر مجاز: {', '.join(provider_map.keys())}"
        )
    return builder()


@lru_cache
def get_ai_provider() -> AIProvider:
    """نمونه‌ی کش‌شده‌ی پروایدر فعال — برای استفاده به‌عنوان DI dependency."""
    return build_ai_provider(get_settings())
