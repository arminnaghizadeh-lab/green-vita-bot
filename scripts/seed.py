"""
Seed script — داده‌ی اولیه‌ی موردنیاز برای شروع کار با پروژه را می‌سازد.

اجرا: python -m scripts.seed
"""

import asyncio

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.db.session import session_scope
from src.repositories.user_repository import UserRepository

logger = get_logger("scripts.seed")


async def seed() -> None:
    configure_logging()
    settings = get_settings()

    async with session_scope() as session:
        user_repo = UserRepository(session)

        for admin_telegram_id in settings.admin_ids:
            user, created = await user_repo.get_or_create(telegram_id=admin_telegram_id)
            if not user.is_admin:
                await user_repo.update(user, is_admin=True)
            action = "created" if created else "updated"
            logger.info("seed_admin_user", telegram_id=admin_telegram_id, action=action)

        if not settings.admin_ids:
            logger.warning(
                "seed_no_admins_configured",
                message="BOT_ADMIN_IDS در .env خالی است — هیچ ادمینی seed نشد.",
            )

    logger.info("seed_completed")


if __name__ == "__main__":
    asyncio.run(seed())
