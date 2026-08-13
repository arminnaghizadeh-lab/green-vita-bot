"""هندلر /help — راهنمای استفاده از ربات (placeholder در فاز ۱)."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")

HELP_TEXT = (
    "🆘 <b>راهنمای گرین ویتا</b>\n\n"
    "دستورات فعلی:\n"
    "/start — شروع و ثبت‌نام\n"
    "/help — نمایش همین راهنما\n"
    "/about — درباره کلینیک گیاه‌پزشکی گرین‌ویتا\n\n"
    "⚠️ امکانات اصلی (تشخیص بیماری، پرونده گیاه، یادآوری، فروشگاه) "
    "هنوز در حال توسعه هستند و در نسخه‌های بعدی فعال می‌شوند."
)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
