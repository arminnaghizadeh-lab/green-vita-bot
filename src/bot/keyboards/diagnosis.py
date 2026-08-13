"""کیبوردهای مربوط به فلوی تشخیص بیماری از روی عکس."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class SkipDetailsCallback(CallbackData, prefix="diagskip"):
    """کاربر می‌تواند از وارد کردن توضیحات اضافه صرف‌نظر کند."""


class ExpertVisitCallback(CallbackData, prefix="expvisit"):
    diagnosis_id: int


def get_skip_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ رد شدن (توضیحی ندارم)", callback_data=SkipDetailsCallback())
    return builder.as_markup()


def get_expert_visit_keyboard(diagnosis_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📞 درخواست ویزیت متخصص گرین‌ویتا",
        callback_data=ExpertVisitCallback(diagnosis_id=diagnosis_id),
    )
    return builder.as_markup()
