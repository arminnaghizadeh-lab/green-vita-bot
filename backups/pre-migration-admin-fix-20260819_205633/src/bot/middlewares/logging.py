"""
Middlewares for the Telegram bot.

- LoggingMiddleware: هر آپدیت ورودی را لاگ می‌کند و خطاهای مدیریت‌نشده را می‌گیرد.
- DBSessionMiddleware: یک AsyncSession تازه به ازای هر آپدیت به هندلر تزریق می‌کند
  (این همان Dependency Injection ساده‌ای است که در aiogram معمول است).
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from src.core.exceptions import GreenVitaError
from src.core.logging import get_logger
from src.db.session import AsyncSessionLocal

logger = get_logger("bot.middleware")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update_id = getattr(event, "update_id", None) if isinstance(event, Update) else None
        logger.info("update_received", update_id=update_id, event_type=type(event).__name__)
        try:
            return await handler(event, data)
        except GreenVitaError as exc:
            logger.warning("handled_app_error", code=exc.code, message=exc.message)
            raise
        except Exception:
            logger.exception("unhandled_bot_error", update_id=update_id)
            raise


class DBSessionMiddleware(BaseMiddleware):
    """هر آپدیت یک AsyncSession جداگانه می‌گیرد تا هندلرها مستقیم به آن دسترسی داشته باشند."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
