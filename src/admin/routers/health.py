"""
Health check endpoint.

Cloud Run و هر load balancer دیگری از این مسیر برای بررسی زنده‌بودن
سرویس و اتصال به دیتابیس استفاده می‌کند.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe ساده — فقط بررسی می‌کند سرویس بالا آمده."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Readiness probe — اتصال واقعی به دیتابیس را هم چک می‌کند."""
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "ai_provider": settings.ai_provider,
        "environment": settings.app_env,
    }
