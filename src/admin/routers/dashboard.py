"""
Dashboard routes.

در فاز ۱ فقط یک صفحه‌ی خلاصه‌وضعیت ساده نمایش داده می‌شود. مدیریت کاربران،
گیاهان و یادآوری‌ها به‌صورت کامل در فازهای بعدی اضافه می‌شود.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Plant, User

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/")
async def dashboard_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    users_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    plants_count = (await session.execute(select(func.count()).select_from(Plant))).scalar_one()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "ai_provider": settings.ai_provider,
            "environment": settings.app_env,
            "users_count": users_count,
            "plants_count": plants_count,
        },
    )
