from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from src.db.models.booking import Service
from src.db.session import AsyncSessionLocal

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/", include_in_schema=False)
async def home(request: Request):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service)
            .where(Service.is_active.is_(True))
            .order_by(Service.id)
        )
        services = result.scalars().all()

    return templates.TemplateResponse(
        "public/home.html",
        {
            "request": request,
            "services": services,
        },
    )


@router.get("/about/", include_in_schema=False)
async def about(request: Request):
    return templates.TemplateResponse(
        "public/about.html",
        {"request": request},
    )


@router.get("/contact/", include_in_schema=False)
async def contact(request: Request):
    return templates.TemplateResponse(
        "public/contact.html",
        {"request": request},
    )
