from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, PlantIdentification, User

router = APIRouter()
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    users_count = await session.scalar(select(func.count()).select_from(User))
    plants_count = await session.scalar(select(func.count()).select_from(Plant))
    diagnoses_count = await session.scalar(select(func.count()).select_from(Diagnosis))
    identifications_count = await session.scalar(
        select(func.count()).select_from(PlantIdentification)
    )
    visits_count = await session.scalar(
        select(func.count())
        .select_from(Diagnosis)
        .where(Diagnosis.expert_visit_requested.is_(True))
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "stats": {
                "users": users_count or 0,
                "plants": plants_count or 0,
                "diagnoses": diagnoses_count or 0,
                "identifications": identifications_count or 0,
                "visits": visits_count or 0,
            },
        },
    )
