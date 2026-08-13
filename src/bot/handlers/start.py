"""هندلر /start — ثبت‌نام خودکار کاربر و خوش‌آمدگویی."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import get_main_menu_keyboard
from src.core.logging import get_logger
from src.repositories.user_repository import UserRepository

logger = get_logger("bot.handlers.start")

router = Router(name="start")

WELCOME_TEXT = (
    "🌿 <b>به دستیار هوشمند گرین ویتا خوش آمدید!</b>\n\n"
    "من دستیار هوشمند کلینیک گیاه‌پزشکی گرین‌ویتا هستم.\n"
    "در نسخه‌ی فعلی، پایه و اسکلت اصلی ربات آماده شده و به‌مرور امکانات زیر فعال می‌شود:\n\n"
    "🌿 تشخیص بیماری گیاه از روی عکس\n"
    "💬 گفتگوی تخصصی گیاه‌پزشکی\n"
    "📅 یادآوری آبیاری و کوددهی\n"
    "📝 پرونده درمانی برای هر گیاه\n"
    "🛒 پیشنهاد محصولات مناسب\n"
    "📞 راهنمایی برای ویزیت حضوری یا آنلاین\n\n"
    "برای شروع از دستور /help استفاده کن."
)


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, created = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )

    if created:
        logger.info("new_user_registered", telegram_id=user.telegram_id)

    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())
