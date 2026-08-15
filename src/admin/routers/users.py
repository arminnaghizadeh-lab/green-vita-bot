"""Admin user management routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, PlantIdentification, User


router = APIRouter(tags=["users"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/users")
async def users_list(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    users = (
        await session.execute(
            select(User).order_by(User.created_at.desc())
        )
    )
    users = users.scalars().all()

    user_rows = []

    for user in users:
        plants_count = (
            await session.execute(
                select(func.count())
                .select_from(Plant)
                .where(Plant.owner_id == user.id)
            )
        ).scalar_one()

        user_rows.append(
            {
                "user": user,
                "plants_count": plants_count,
            }
        )

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "environment": settings.app_env,
            "users": user_rows,
        },
    )


@router.get("/users/{user_id}")
async def user_detail(
    request: Request,
    user_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    user = (
        await session.execute(
            select(User).where(User.id == user_id)
        )
    ).scalar_one_or_none()

    if user is None:
        return RedirectResponse(url="/users", status_code=303)

    plants = (
        await session.execute(
            select(Plant)
            .where(Plant.owner_id == user.id)
            .order_by(Plant.created_at.desc())
        )
    ).scalars().all()

    diagnoses_count = (
        await session.execute(
            select(func.count())
            .select_from(Diagnosis)
            .where(Diagnosis.user_id == user.id)
        )
    ).scalar_one()

    identifications_count = (
        await session.execute(
            select(func.count())
            .select_from(PlantIdentification)
            .where(PlantIdentification.user_id == user.id)
        )
    ).scalar_one()

    plant_rows = []
    for plant in plants:
        plant_diagnoses_count = (
            await session.execute(
                select(func.count())
                .select_from(Diagnosis)
                .where(Diagnosis.plant_id == plant.id)
            )
        ).scalar_one()

        plant_rows.append(
            {
                "plant": plant,
                "diagnoses_count": plant_diagnoses_count,
            }
        )

    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "environment": settings.app_env,
            "user": user,
            "plants": plant_rows,
            "diagnoses_count": diagnoses_count,
            "identifications_count": identifications_count,
        },
    )
