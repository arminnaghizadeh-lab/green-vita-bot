"""
Dashboard routes.

در فاز ۱ فقط یک صفحه‌ی خلاصه‌وضعیت ساده نمایش داده می‌شود. مدیریت کاربران،
گیاهان و یادآوری‌ها به‌صورت کامل در فازهای بعدی اضافه می‌شود.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, User

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/")
async def dashboard_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    users_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    plants_count = (await session.execute(select(func.count()).select_from(Plant))).scalar_one()
    visits_new_count = (
        await session.execute(
            select(func.count())
            .select_from(Diagnosis)
            .where(Diagnosis.expert_visit_requested.is_(True))
            .where(Diagnosis.expert_visit_status == "new")
        )
    ).scalar_one()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "ai_provider": settings.ai_provider,
            "environment": settings.app_env,
            "users_count": users_count,
            "plants_count": plants_count,
            "visits_new_count": visits_new_count,
        },
    )
