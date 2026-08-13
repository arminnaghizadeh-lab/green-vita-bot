"""Shared FastAPI dependencies (Dependency Injection layer for the admin panel)."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.db.session import get_db_session

# در فاز ۱ فقط dependency های پایه — احراز هویت واقعی در فاز بعد اضافه می‌شود.


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_app_settings() -> Settings:
    return get_settings()
