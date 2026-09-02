"""Admin PWA Web Push endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.db.models.push_subscription import PushSubscription
from src.db.session import get_db_session


router = APIRouter()


@router.get("/api/push/vapid-public-key")
async def vapid_public_key(request: Request):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    public_key = os.getenv("VAPID_PUBLIC_KEY", "").strip()

    if not public_key:
        return JSONResponse(
            {"error": "VAPID_PUBLIC_KEY is not configured"},
            status_code=503,
        )

    return JSONResponse({"public_key": public_key})


@router.post("/api/push/subscribe")
async def subscribe_push(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid JSON"},
            status_code=400,
        )

    endpoint = str(payload.get("endpoint", "")).strip()
    keys = payload.get("keys") or {}

    p256dh = str(keys.get("p256dh", "")).strip()
    auth = str(keys.get("auth", "")).strip()

    if not endpoint or not p256dh or not auth:
        return JSONResponse(
            {"error": "Invalid push subscription"},
            status_code=400,
        )

    user_agent = request.headers.get("user-agent")

    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint
        )
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        subscription = PushSubscription(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
            is_active=True,
        )
        session.add(subscription)
    else:
        subscription.p256dh = p256dh
        subscription.auth = auth
        subscription.user_agent = user_agent
        subscription.is_active = True

    await session.commit()

    return JSONResponse({
        "ok": True,
        "message": "Push subscription saved",
    })


@router.delete("/api/push/subscribe")
async def unsubscribe_push(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    endpoint = str(payload.get("endpoint", "")).strip()

    if endpoint:
        result = await session.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription is not None:
            subscription.is_active = False
            await session.commit()

    return JSONResponse({"ok": True})


@router.get("/api/push/status")
async def push_status(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.is_active.is_(True)
        )
    )
    subscriptions = result.scalars().all()

    return JSONResponse({
        "configured": bool(os.getenv("VAPID_PUBLIC_KEY", "").strip()),
        "active_subscriptions": len(subscriptions),
    })
