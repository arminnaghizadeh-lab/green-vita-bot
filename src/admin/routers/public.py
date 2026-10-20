from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
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



@router.get("/robots.txt", include_in_schema=False)
async def robots():
    content = """User-agent: *
Allow: /

Sitemap: https://greenvitaclinic.ir/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    from xml.sax.saxutils import escape

    urls = [
        "https://greenvitaclinic.ir/",
        "https://greenvitaclinic.ir/about/",
        "https://greenvitaclinic.ir/contact/",
        "https://greenvitaclinic.ir/booking/",
    ]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Service)
            .where(Service.is_active.is_(True))
            .order_by(Service.id)
        )
        services = result.scalars().all()

    for service in services:
        urls.append(
            f"https://greenvitaclinic.ir/booking/service/{service.id}/"
        )

    items = []
    for url in urls:
        items.append(f"    <url><loc>{escape(url)}</loc></url>")

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
""" % "\n".join(items)

    return Response(content=xml, media_type="application/xml")


@router.get("/about/", include_in_schema=False)
async def about(request: Request):
    return templates.TemplateResponse(
        "public/about.html",
        {"request": request},
    )



@router.get("/call/", include_in_schema=False)
async def call():
    return RedirectResponse(
        url="tel:+989128111058",
        status_code=302,
    )

@router.get("/contact/", include_in_schema=False)
async def contact(request: Request):
    return templates.TemplateResponse(
        "public/contact.html",
        {"request": request},
    )
