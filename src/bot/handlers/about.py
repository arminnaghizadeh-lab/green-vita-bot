"""هندلر درباره کلینیک گیاهپزشکی گرین ویتا."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards.main_menu import BTN_ABOUT
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router(name="about")

ABOUT_TEXT = (
    "🌿 کلینیک گیاه‌پزشکی گرین ویتا\n\n"
    "گرین ویتا در زمینه گیاهان و گیاه‌پزشکی فعالیت می‌کند و "
    "برای نگهداری بهتر و درمان اصولی گیاهان خدمات تخصصی ارائه می‌دهد.\n\n"
    "📞 شماره تماس:\n"
    "۰۹۱۲۸۱۱۱۰۵۸"
)


ABOUT_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📩 ارسال پیام در واتساپ",
                url="https://wa.me/message/3TYFRDAI5SAMM1",
            )
        ],
        [
            InlineKeyboardButton(
                text="📷 صفحه اینستاگرام گرین ویتا",
                url="https://www.instagram.com/greenvita_clinic/",
            )
        ],
        [
            InlineKeyboardButton(
                text="📍 آدرس ما",
                url="https://nshn.ir/rbvZlRPxVSMS",
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 سایت گرین ویتا",
                url="https://Greenvitaclinic.ir",
            )
        ],
        [
            InlineKeyboardButton(
                text="🤖 دستیار هوشمند بله",
                url="https://ble.ir/greenvita_ai_bot",
            )
        ],
    ]
)


@router.message(Command("about"))
@router.message(lambda message: message.text == BTN_ABOUT)
async def handle_about(message: Message) -> None:
    await message.answer(
        ABOUT_TEXT,
        reply_markup=ABOUT_MENU,
    )

