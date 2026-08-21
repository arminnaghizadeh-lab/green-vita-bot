"""کیبوردهای مربوط به فلوی پرونده گیاه (لیست/افزودن/مشاهده/حذف)."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models.plant import Plant


class ViewPlantCallback(CallbackData, prefix="plantview"):
    plant_id: int


class AddPlantCallback(CallbackData, prefix="plantadd"):
    pass


class SkipSpeciesCallback(CallbackData, prefix="plantskipsp"):
    pass


class DeletePlantCallback(CallbackData, prefix="plantdel"):
    plant_id: int


class ConfirmDeletePlantCallback(CallbackData, prefix="plantdelok"):
    plant_id: int


class BackToPlantListCallback(CallbackData, prefix="plantback"):
    pass


def get_my_plants_keyboard(plants: list[Plant]) -> InlineKeyboardMarkup:
    """لیست گیاهان کاربر + دکمه‌ی افزودن گیاه جدید."""
    builder = InlineKeyboardBuilder()
    for plant in plants:
        builder.button(
            text=f"🌱 {plant.name}",
            callback_data=ViewPlantCallback(plant_id=plant.id),
        )
    builder.button(text="➕ افزودن گیاه جدید", callback_data=AddPlantCallback())
    builder.adjust(1)
    return builder.as_markup()


def get_skip_species_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ رد شدن (نوعش رو نمی‌دونم)", callback_data=SkipSpeciesCallback())
    return builder.as_markup()


def get_plant_detail_keyboard(plant_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 حذف این گیاه", callback_data=DeletePlantCallback(plant_id=plant_id))
    builder.button(text="⬅️ بازگشت به لیست گیاهان", callback_data=BackToPlantListCallback())
    builder.adjust(1)
    return builder.as_markup()


def get_delete_confirmation_keyboard(plant_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ بله، حذف کن", callback_data=ConfirmDeletePlantCallback(plant_id=plant_id)
    )
    builder.button(text="❌ نه، بی‌خیال", callback_data=ViewPlantCallback(plant_id=plant_id))
    builder.adjust(1)
    return builder.as_markup()
