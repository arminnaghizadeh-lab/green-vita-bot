from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.core.config import Settings, get_settings
from src.db.models import Diagnosis, Plant, PlantIdentification, User, SmartBioClick

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

    smart_bio_total = await session.scalar(
        select(func.count()).select_from(SmartBioClick)
    )

    smart_bio_channel_rows = (
        await session.execute(
            select(
                SmartBioClick.channel,
                func.count().label("count"),
            )
            .group_by(SmartBioClick.channel)
            .order_by(func.count().desc())
        )
    ).all()

    smart_bio_channels = {
        row.channel: row.count
        for row in smart_bio_channel_rows
    }

    smart_bio_channel_total = sum(smart_bio_channels.values())

    smart_bio_channel_stats = []
    for channel, count in smart_bio_channels.items():
        percentage = (
            round((count / smart_bio_channel_total) * 100, 1)
            if smart_bio_channel_total
            else 0
        )

        smart_bio_channel_stats.append(
            {
                "channel": channel,
                "count": count,
                "percentage": percentage,
            }
        )

    smart_bio_channel_stats.sort(
        key=lambda item: item["count"],
        reverse=True,
    )

    smart_bio_top_channel = (
        smart_bio_channel_stats[0]
        if smart_bio_channel_stats
        else None
    )

    smart_bio_recent_rows = (
        await session.execute(
            select(
                SmartBioClick.channel,
                SmartBioClick.source_path,
                SmartBioClick.created_at,
            )
            .order_by(SmartBioClick.created_at.desc())
            .limit(10)
        )
    ).all()


    now_utc = datetime.now(timezone.utc)
    day_ago = now_utc - timedelta(days=1)
    week_ago = now_utc - timedelta(days=7)

    smart_bio_24h = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= day_ago)
    )

    smart_bio_7d = await session.scalar(
        select(func.count())
        .select_from(SmartBioClick)
        .where(SmartBioClick.created_at >= week_ago)
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
            "smart_bio": {
                "total": smart_bio_total or 0,
                "channels": smart_bio_channels,
                "channel_stats": smart_bio_channel_stats,
                "top_channel": smart_bio_top_channel,
                "recent": smart_bio_recent_rows,
                "last_24h": smart_bio_24h or 0,
                "last_7d": smart_bio_7d or 0,
            },
        },
    )
