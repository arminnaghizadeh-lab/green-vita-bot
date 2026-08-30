"""کیبورد منوی اصلی بات."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_START = "🏠 شروع"
BTN_DIAGNOSE = "📷 تشخیص بیماری"
BTN_IDENTIFY = "🔍 شناسایی گیاه"
BTN_EXPERT_VISIT = "📞 درخواست ویزیت متخصص"
BTN_MY_PLANTS = "🌱 گیاهان من"
BTN_ABOUT = "ℹ️ درباره ما"
BTN_HELP = "🆘 راهنما"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """منوی اصلی بات."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_START)],
            [KeyboardButton(text=BTN_DIAGNOSE), KeyboardButton(text=BTN_IDENTIFY)],
            [KeyboardButton(text=BTN_EXPERT_VISIT)],
            [KeyboardButton(text=BTN_MY_PLANTS)],
            [KeyboardButton(text=BTN_ABOUT), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
)
