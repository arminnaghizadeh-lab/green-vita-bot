"""هندلر درباره کلینیک گیاهپزشکی گرین ویتا."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards.main_menu import BTN_ABOUT

router = Router(name="about")

ABOUT_TEXT = (
    "🌿 <b>کلینیک گیاهپزشکی گرین ویتا</b>\n\n"
    "گرین ویتا یک کلینیک تخصصی در زمینه گیاهان و گیاه‌پزشکی است "
    "که با هدف کمک به نگهداری بهتر و درمان اصولی گیاهان فعالیت می‌کند.\n\n"
    "📞 <b>شماره تماس:</b>\n"
    "۰۹۱۲۸۱۱۱۰۵۸\n\n"
    "💬 <b>واتساپ:</b>\n"
    '<a href="https://wa.me/message/3TYFRDAI5SAMM1">ارتباط در واتساپ</a>\n\n'
    "📷 <b>اینستاگرام:</b>\n"
    '<a href="https://www.instagram.com/greenvita_clinic/">@greenvita_clinic</a>\n\n'
    "📍 <b>مسیریابی:</b>\n"
    '<a href="https://nshn.ir/rbvZlRPxVSMS">مشاهده موقعیت در نشان</a>\n\n'
    "🌐 <b>وب‌سایت:</b>\n"
    "Greenvita_clinic.ir"
)


@router.message(Command("about"))
@router.message(lambda message: message.text == BTN_ABOUT)
async def handle_about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)
