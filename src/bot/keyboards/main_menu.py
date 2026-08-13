"""کیبوردهای بات."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_DIAGNOSE = "📷 تشخیص بیماری"
BTN_IDENTIFY = "🔍 شناسایی گیاه"
BTN_ABOUT = "ℹ️ درباره ما"
BTN_HELP = "🆘 راهنما"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    منوی اصلی — دکمه‌های باقی‌مانده (پرونده گیاه، یادآوری، فروشگاه)
    در فازهای بعدی به این کیبورد اضافه می‌شوند.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DIAGNOSE), KeyboardButton(text=BTN_IDENTIFY)],
            [KeyboardButton(text=BTN_ABOUT), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )
