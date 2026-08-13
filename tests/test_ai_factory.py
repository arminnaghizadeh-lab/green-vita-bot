"""تست‌های src.ai.factory — مطمئن می‌شویم سوییچ پروایدر با env درست کار می‌کند."""

import pytest

from src.ai.factory import build_ai_provider
from src.ai.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.core.config import Settings
from src.core.exceptions import ConfigurationError, AIProviderError


def test_build_ai_provider_claude():
    settings = Settings(ai_provider="claude", anthropic_api_key="key", anthropic_model="claude-sonnet-4-6")
    provider = build_ai_provider(settings)
    assert isinstance(provider, ClaudeProvider)
    assert provider.name == "claude"


def test_build_ai_provider_gemini():
    settings = Settings(ai_provider="gemini", gemini_api_key="key", gemini_model="gemini-2.0-flash")
    provider = build_ai_provider(settings)
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


def test_build_ai_provider_openai():
    settings = Settings(ai_provider="openai", openai_api_key="key", openai_model="gpt-4o")
    provider = build_ai_provider(settings)
    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"


def test_build_ai_provider_openai_with_custom_base_url():
    """مثل تنظیم gatewayهای سازگار با OpenAI (مثل AvalAI) برای دسترسی به Claude."""
    settings = Settings(
        ai_provider="openai",
        openai_api_key="key",
        openai_model="claude-sonnet-4-6",
        openai_base_url="https://api.avalai.ir/v1",
    )
    provider = build_ai_provider(settings)
    assert isinstance(provider, OpenAIProvider)
    assert str(provider.client.base_url) == "https://api.avalai.ir/v1/"


def test_build_ai_provider_openai_without_base_url_uses_default():
    """اگر OPENAI_BASE_URL خالی باشد، رفتار قبلی (آدرس رسمی OpenAI) حفظ می‌شود."""
    settings = Settings(ai_provider="openai", openai_api_key="key", openai_base_url="")
    provider = build_ai_provider(settings)
    assert "avalai" not in str(provider.client.base_url)


def test_build_ai_provider_missing_key_raises():
    settings = Settings(ai_provider="claude", anthropic_api_key="")
    with pytest.raises(AIProviderError):
        build_ai_provider(settings)


def test_build_ai_provider_invalid_provider_raises():
    settings = Settings.model_construct(ai_provider="unknown-provider")
    with pytest.raises(ConfigurationError):
        build_ai_provider(settings)
