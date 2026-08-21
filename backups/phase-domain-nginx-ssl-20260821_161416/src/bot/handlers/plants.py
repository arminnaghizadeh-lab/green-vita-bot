"""
هندلر پرونده‌ی گیاه — ثبت، مشاهده، حذف گیاهان کاربر.

فلو:
1. کاربر «🌱 گیاهان من» یا /plants را می‌زند → لیست گیاهانش (یا پیام خالی بودن لیست).
2. «➕ افزودن گیاه جدید» → اسم گیاه پرسیده می‌شود، بعد نوع/گونه (اختیاری، قابل رد شدن).
3. با زدن روی هر گیاه در لیست، جزئیاتش (نام، نوع، وضعیت سلامت) نمایش داده می‌شود،
   همراه با دکمه‌ی حذف (با یک تأیید میانی برای جلوگیری از حذف تصادفی).

این فیچر مستقل از فلوهای تشخیص بیماری/شناسایی گیاه است — چیزی در آن دو فایل تغییر نکرده.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    AddPlantCallback,
    BackToPlantListCallback,
    ConfirmDeletePlantCallback,
    DeletePlantCallback,
    SkipSpeciesCallback,
    ViewPlantCallback,
    get_delete_confirmation_keyboard,
    get_my_plants_keyboard,
    get_plant_detail_keyboard,
    get_skip_species_keyboard,
)
from src.bot.keyboards.main_menu import BTN_MY_PLANTS
from src.bot.states import PlantStates
from src.core.logging import get_logger
from src.db.models.plant import Plant, PlantHealthStatus
from src.repositories.plant_repository import PlantRepository
from src.repositories.user_repository import UserRepository

logger = get_logger("bot.handlers.plants")

router = Router(name="plants")

_HEALTH_LABEL = {
    PlantHealthStatus.HEALTHY: "🟢 سالم",
    PlantHealthStatus.SICK: "🔴 بیمار",
    PlantHealthStatus.UNDER_TREATMENT: "🟡 در حال درمان",
    PlantHealthStatus.RECOVERED: "✅ بهبودیافته",
    PlantHealthStatus.UNKNOWN: "⚪️ نامشخص",
}

_ASK_NAME_TEXT = "🌱 اسم این گیاه رو چی می‌ذاری؟ (مثلاً: «مونستِرای اتاق پذیرایی»)"
_ASK_SPECIES_TEXT = (
    "🔍 نوع/گونه‌ی این گیاه رو می‌دونی؟ (مثلاً: مونستِرا، پتوس، ارکیده...)\n"
    "اگه نمی‌دونی، دکمه‌ی زیر رو بزن."
)
_EMPTY_LIST_TEXT = "هنوز هیچ گیاهی ثبت نکردی. با دکمه‌ی زیر اولین پرونده‌ی گیاهت رو بساز 🌱"
_LIST_HEADER_TEXT = "🌱 <b>گیاهان من</b>\n\nروی هرکدوم بزن تا جزئیاتش رو ببینی:"


def _format_plant_detail(plant: Plant) -> str:
    lines = [f"🌱 <b>{plant.name}</b>"]
    lines.append(f"🔍 نوع/گونه: {plant.species or 'نامشخص'}")
    lines.append(f"📊 وضعیت سلامت: {_HEALTH_LABEL.get(plant.health_status, '⚪️ نامشخص')}")
    if plant.notes:
        lines.append(f"\n📝 یادداشت: {plant.notes}")
    return "\n".join(lines)


async def _get_owned_plant(
    plant_repo: PlantRepository, plant_id: int, user_id: int
) -> Plant | None:
    """گیاه را برمی‌گرداند فقط اگر واقعاً متعلق به همین کاربر باشد (جلوگیری از دسترسی به گیاه دیگران)."""
    plant = await plant_repo.get_by_id(plant_id)
    if plant is None or plant.owner_id != user_id:
        return None
    return plant


@router.message(Command("plants"))
@router.message(F.text == BTN_MY_PLANTS)
async def handle_my_plants(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    plants = await plant_repo.list_by_owner(user.id)

    if not plants:
        await message.answer(_EMPTY_LIST_TEXT, reply_markup=get_my_plants_keyboard([]))
        return

    await message.answer(_LIST_HEADER_TEXT, reply_markup=get_my_plants_keyboard(plants))


@router.callback_query(BackToPlantListCallback.filter())
async def handle_back_to_list(callback: CallbackQuery, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    plants = await plant_repo.list_by_owner(user.id)

    await callback.answer()
    text = _LIST_HEADER_TEXT if plants else _EMPTY_LIST_TEXT
    await callback.message.edit_text(text, reply_markup=get_my_plants_keyboard(plants))


@router.callback_query(AddPlantCallback.filter())
async def handle_add_plant_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PlantStates.waiting_name)
    await callback.answer()
    await callback.message.answer(_ASK_NAME_TEXT)


@router.message(PlantStates.waiting_name, F.text)
async def handle_plant_name_received(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer(_ASK_NAME_TEXT)
        return

    await state.update_data(plant_name=name)
    await state.set_state(PlantStates.waiting_species)
    await message.answer(_ASK_SPECIES_TEXT, reply_markup=get_skip_species_keyboard())


async def _create_plant_and_reply(
    *, message_target: Message, session: AsyncSession, telegram_user_id: int, name: str, species: str | None
) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(telegram_id=telegram_user_id)
    plant = await plant_repo.create(owner_id=user.id, name=name, species=species)

    await message_target.answer(
        f"✅ پرونده‌ی «{plant.name}» ساخته شد.\n\n" + _format_plant_detail(plant),
        reply_markup=get_plant_detail_keyboard(plant.id),
    )


@router.message(PlantStates.waiting_species, F.text)
async def handle_plant_species_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()

    name = data.get("plant_name")
    if not name:
        await message.answer("این درخواست منقضی شده. دوباره از «🌱 گیاهان من» شروع کن.")
        return

    await _create_plant_and_reply(
        message_target=message,
        session=session,
        telegram_user_id=message.from_user.id,
        name=name,
        species=message.text.strip(),
    )


@router.callback_query(PlantStates.waiting_species, SkipSpeciesCallback.filter())
async def handle_skip_species(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    name = data.get("plant_name")
    if not name:
        await callback.message.edit_text("این درخواست منقضی شده. دوباره از «🌱 گیاهان من» شروع کن.")
        return

    await _create_plant_and_reply(
        message_target=callback.message,
        session=session,
        telegram_user_id=callback.from_user.id,
        name=name,
        species=None,
    )


@router.callback_query(ViewPlantCallback.filter())
async def handle_view_plant(
    callback: CallbackQuery, callback_data: ViewPlantCallback, session: AsyncSession
) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    plant = await _get_owned_plant(plant_repo, callback_data.plant_id, user.id)

    if not plant:
        await callback.answer("این گیاه پیدا نشد.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        _format_plant_detail(plant), reply_markup=get_plant_detail_keyboard(plant.id)
    )


@router.callback_query(DeletePlantCallback.filter())
async def handle_delete_plant_request(
    callback: CallbackQuery, callback_data: DeletePlantCallback, session: AsyncSession
) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    plant = await _get_owned_plant(plant_repo, callback_data.plant_id, user.id)

    if not plant:
        await callback.answer("این گیاه پیدا نشد.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        f"⚠️ مطمئنی می‌خوای پرونده‌ی «{plant.name}» رو حذف کنی؟ این کار قابل‌برگشت نیست.",
        reply_markup=get_delete_confirmation_keyboard(plant.id),
    )


@router.callback_query(ConfirmDeletePlantCallback.filter())
async def handle_delete_plant_confirmed(
    callback: CallbackQuery, callback_data: ConfirmDeletePlantCallback, session: AsyncSession
) -> None:
    user_repo = UserRepository(session)
    plant_repo = PlantRepository(session)

    user, _ = await user_repo.get_or_create(telegram_id=callback.from_user.id)
    plant = await _get_owned_plant(plant_repo, callback_data.plant_id, user.id)

    if not plant:
        await callback.answer("این گیاه پیدا نشد.", show_alert=True)
        return

    plant_name = plant.name
    await plant_repo.delete(plant)
    logger.info("plant_deleted", plant_id=callback_data.plant_id, telegram_user_id=callback.from_user.id)

    await callback.answer("حذف شد ✅", show_alert=True)

    plants = await plant_repo.list_by_owner(user.id)
    text = f"🗑 پرونده‌ی «{plant_name}» حذف شد.\n\n" + (
        _LIST_HEADER_TEXT if plants else _EMPTY_LIST_TEXT
    )
    await callback.message.edit_text(text, reply_markup=get_my_plants_keyboard(plants))
