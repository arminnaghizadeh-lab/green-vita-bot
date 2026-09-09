"""Persistent conversation state/data for the Bale bot."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from src.core.config import get_settings


_PREFIX = "bale:state:"
_TTL = 30 * 60


def _redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def set_state(bale_id: int, state: str) -> None:
    redis = _redis()
    try:
        await redis.set(
            f"{_PREFIX}{bale_id}",
            state,
            ex=_TTL,
        )
    finally:
        await redis.aclose()


async def get_state(bale_id: int) -> str | None:
    redis = _redis()
    try:
        return await redis.get(f"{_PREFIX}{bale_id}")
    finally:
        await redis.aclose()


async def set_data(bale_id: int, data: dict[str, Any]) -> None:
    redis = _redis()
    try:
        state_key = f"{_PREFIX}{bale_id}:data"
        await redis.set(
            state_key,
            json.dumps(data, ensure_ascii=False),
            ex=_TTL,
        )
    finally:
        await redis.aclose()


async def get_data(bale_id: int) -> dict[str, Any]:
    redis = _redis()
    try:
        raw = await redis.get(f"{_PREFIX}{bale_id}:data")
        if not raw:
            return {}

        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        return value if isinstance(value, dict) else {}
    finally:
        await redis.aclose()


async def update_data(bale_id: int, **values: Any) -> dict[str, Any]:
    data = await get_data(bale_id)
    data.update(values)
    await set_data(bale_id, data)
    return data


async def clear_state(bale_id: int) -> None:
    redis = _redis()
    try:
        await redis.delete(
            f"{_PREFIX}{bale_id}",
            f"{_PREFIX}{bale_id}:data",
        )
    finally:
        await redis.aclose()
