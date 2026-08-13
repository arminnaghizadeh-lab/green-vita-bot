"""Shared pytest fixtures."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# قبل از هر ایمپورت از src.core.config، env تست را ست می‌کنیم
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("AI_PROVIDER", "claude")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "development")

from src.core.config import get_settings  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.db.models import *  # noqa: E402,F401,F403


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """هر تست با کش تنظیمات تازه شروع شود."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """یک دیتابیس SQLite in-memory تازه برای هر تست."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()
