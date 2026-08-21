"""
Telegram bot entrypoint.

اجرا: python -m src.bot.main
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from src.ai.factory import get_ai_provider
from src.bot.handlers import get_root_router
from src.bot.middlewares import DBSessionMiddleware, LoggingMiddleware
from src.core.config import Settings, get_settings
from src.core.exceptions import AIProviderError, ConfigurationError
from src.core.logging import configure_logging, get_logger

logger = get_logger("bot.main")


def _build_storage(settings: Settings) -> RedisStorage | MemoryStorage:
    """
    FSM (مثل انتخاب گیاه بعد از فرستادن عکس) باید در Redis نگه داشته شود تا
    با ری‌استارت شدن سرویس یا اسکیل‌شدن به چند نمونه از دست نرود.
    اگر Redis در دسترس نبود (مثلاً تست لوکال سریع)، به MemoryStorage سقوط می‌کنیم.
    """
    try:
        return RedisStorage.from_url(settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_storage_unavailable_falling_back", error=str(exc))
        return MemoryStorage()


def create_dispatcher(settings: Settings) -> Dispatcher:
    dp = Dispatcher(storage=_build_storage(settings))
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.include_router(get_root_router())
    return dp


async def run_bot() -> None:
    configure_logging()
    settings = get_settings()

    if not settings.bot_token:
        raise ConfigurationError("BOT_TOKEN تنظیم نشده است. آن را در فایل .env قرار بده.")

    try:
        get_ai_provider()
    except (AIProviderError, ConfigurationError) as exc:
        logger.error("ai_provider_misconfigured", ai_provider=settings.ai_provider, error=exc.message)
        raise

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher(settings)

    logger.info("bot_starting", app_env=settings.app_env, ai_provider=settings.ai_provider)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("bot_stopped")


def main() -> None:
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("bot_interrupted")


if __name__ == "__main__":
    main()
