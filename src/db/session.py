"""
Async SQLAlchemy engine & session factory.

از یک Engine سراسری استفاده می‌کنیم و برای هر واحد کار (unit of work)
یک Session جدید از طریق get_db_session می‌سازیم — مناسب برای هم بات و هم API.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

settings = get_settings()

_engine_kwargs: dict = {"echo": settings.debug and not settings.is_production, "future": True}

# SQLite در حالت async به pool سفارشی نیاز ندارد، ولی Postgres برای Cloud Run
# به pool_pre_ping نیاز دارد تا کانکشن‌های مرده را قبل از استفاده رد کند.
if not settings.is_sqlite:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10)

engine: AsyncEngine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI/aiogram dependency: yields a session and guarantees closure."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside of DI frameworks (e.g. scripts, jobs)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
