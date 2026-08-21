"""هندلر راهنمای استفاده از ربات گرین ویتا."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards.main_menu import BTN_HELP

router = Router(name="help")

HELP_TEXT = """
🆘 <b>راهنمای استفاده از گرین ویتا</b>

🌿 <b>منوی اصلی</b>
از دکمه‌های منوی پایین صفحه برای استفاده از امکانات ربات استفاده کن.

📷 <b>تشخیص بیماری</b>
اگر گیاهت بیمار یا دچار مشکل شده، از این بخش برای ارسال عکس و دریافت بررسی هوشمند وضعیت گیاه استفاده کن.

🔍 <b>شناسایی گیاه</b>
اگر اسم گیاهت را نمی‌دانی، عکس آن را ارسال کن تا ربات برای شناسایی گونه و ارائه راهنمای نگهداری آن تلاش کند.

ℹ️ <b>درباره ما</b>
اطلاعات کلینیک گیاهپزشکی گرین ویتا و راه‌های ارتباطی را مشاهده کن.

🏠 <b>شروع</b>
برای بازگشت به منوی اصلی از دکمه «🏠 شروع» استفاده کن.

💡 <b>نکته:</b>
برای تشخیص بهتر، عکس واضح و با نور مناسب از گیاه یا قسمت آسیب‌دیده ارسال کن.
""".strip()


@router.message(Command("help"))
@router.message(lambda message: message.text == BTN_HELP)
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
