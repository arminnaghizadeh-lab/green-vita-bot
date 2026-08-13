"""تست‌های src.core.config"""

import os

from src.core.config import Settings, get_settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc:123")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.bot_token == "abc:123"
    assert settings.ai_provider == "gemini"


def test_admin_ids_parsing():
    settings = Settings(bot_admin_ids="111, 222,333")
    assert settings.admin_ids == [111, 222, 333]


def test_admin_ids_empty_string():
    settings = Settings(bot_admin_ids="")
    assert settings.admin_ids == []


def test_database_url_normalizes_postgres_scheme():
    settings = Settings(database_url="postgres://user:pass@host:5432/db")
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_is_sqlite_true_for_sqlite_url():
    settings = Settings(database_url="sqlite+aiosqlite:///./test.db")
    assert settings.is_sqlite is True


def test_is_production_flag():
    settings = Settings(app_env="production")
    assert settings.is_production is True
    settings_dev = Settings(app_env="development")
    assert settings_dev.is_production is False


def test_get_settings_is_cached():
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
