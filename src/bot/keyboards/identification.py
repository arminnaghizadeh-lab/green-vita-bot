"""کیبوردهای مربوط به فلوی شناسایی گونه گیاه از روی عکس."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class DiagnoseFromIdentificationCallback(CallbackData, prefix="iddiag"):
    identification_id: int


class IdentificationExpertVisitCallback(CallbackData, prefix="idexpvisit"):
    identification_id: int


def get_identification_result_keyboard(identification_id: int) -> InlineKeyboardMarkup:
    """دو دکمه‌ی زیر نتیجه‌ی شناسایی: تشخیص بیماری همین گیاه، یا درخواست ویزیت متخصص."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🩺 تشخیص بیماری",
        callback_data=DiagnoseFromIdentificationCallback(identification_id=identification_id),
    )
    builder.button(
        text="📞 درخواست ویزیت متخصص گرین‌ویتا",
        callback_data=IdentificationExpertVisitCallback(identification_id=identification_id),
    )
    builder.adjust(1)
    return builder.as_markup()
