"""Web Push service for Green Vita admin PWA."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def _vapid_private_key() -> str:
    value = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    if not value:
        raise RuntimeError("VAPID_PRIVATE_KEY is not configured")
    return value


def _vapid_subject() -> str:
    value = os.getenv("VAPID_SUBJECT", "").strip()
    if not value:
        raise RuntimeError("VAPID_SUBJECT is not configured")
    return value


async def send_push(
    session: AsyncSession,
    *,
    title: str,
    body: str,
    url: str = "/visits",
    badge_count: int | None = None,
) -> int:
    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.is_active.is_(True)
        )
    )
    subscriptions = result.scalars().all()

    if not subscriptions:
        return 0

    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "url": url,
    }

    if badge_count is not None:
        payload["badge_count"] = max(0, int(badge_count))

    sent = 0

    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=_vapid_private_key(),
                vapid_claims={
                    "sub": _vapid_subject(),
                },
            )
            sent += 1

        except WebPushException as exc:
            status_code = getattr(
                getattr(exc, "response", None),
                "status_code",
                None,
            )

            if status_code in (404, 410):
                subscription.is_active = False
                logger.info(
                    "Deactivated expired push subscription id=%s",
                    subscription.id,
                )
            else:
                logger.warning(
                    "Web Push failed for subscription id=%s: %s",
                    subscription.id,
                    exc,
                )

        except Exception:
            logger.exception(
                "Unexpected Web Push error for subscription id=%s",
                subscription.id,
            )

    await session.commit()
    return sent
