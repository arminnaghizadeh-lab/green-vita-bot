"""Public Smart Bio Link routes and click tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.smart_bio_click import SmartBioClick
from src.db.session import get_db_session


router = APIRouter()


SMART_BIO_TARGETS: dict[str, str] = {
    "telegram": "https://t.me/GreenVita_Al_Bot",
    "instagram": "https://www.instagram.com/greenvita_clinic",
    "whatsapp": "https://wa.me/989128111058",
    "bale": "https://ble.ir/greenvita",
}


@router.get("/go/{channel}")
async def smart_bio_redirect(
    channel: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    target = SMART_BIO_TARGETS.get(channel)

    if target is None:
        return RedirectResponse("/", status_code=302)

    click = SmartBioClick(
        channel=channel,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        source_path=request.url.path,
    )

    session.add(click)
    await session.commit()

    return RedirectResponse(target, status_code=302)
