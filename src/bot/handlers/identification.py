"""
هندلر شناسایی گونه گیاه از روی عکس.

فلو:
1. کاربر دکمه‌ی «🔍 شناسایی گیاه» یا دستور /identify را می‌زند.
2. عکس گیاه را می‌فرستد.
3. عکس به AI Provider فعال فرستاده می‌شود و گونه + راهنمای کامل نگهداری برمی‌گردد.
4. نتیجه ذخیره و برای کاربر با دو دکمه نمایش داده می‌شود:
   «🩺 تشخیص بیماری» (که مستقیم وارد فلوی diagnosis می‌شود، با اسم گونه‌ی شناسایی‌شده)
   و «📞 درخواست ویزیت متخصص گرین‌ویتا».
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.factory import get_ai_provider
from src.ai.plant_identification import PlantIdentificationResult, identify_plant_image
from src.bot.keyboards import (
    DiagnoseFromIdentificationCallback,
    IdentificationExpertVisitCallback,
    get_identification_result_keyboard,
    get_skip_details_keyboard,
)
from src.bot.keyboards.main_menu import BTN_IDENTIFY
from src.bot.states import DiagnosisStates, IdentificationStates
from src.core.config import get_settings
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger
from src.db.models.plant_identification import DifficultyLevel, PlantIdentification
from src.repositories.plant_identification_repository import PlantIdentificationRepository
from src.repositories.user_repository import UserRepository

logger = get_logger("bot.handlers.identification")

router = Router(name="identification")

_DIFFICULTY_LABEL = {
    DifficultyLevel.EASY: "🟢 آسان",
    DifficultyLevel.MEDIUM: "🟡 متوسط",
    DifficultyLevel.HARD: "🔴 سخت",
    DifficultyLevel.UNKNOWN: "⚪️ نامشخص",
}

_IDENTIFY_INTRO_TEXT = (
    "🔍 یک عکس واضح از کل گیاه یا برگ‌هاش بفرست تا گونه‌اش رو شناسایی کنم و "
    "راهنمای کامل نگهداریش رو برات بفرستم."
)

_ASK_FOR_PHOTO_TEXT = "📷 برای شناسایی گیاه، لطفاً یک عکس بفرست."

_DISCLAIMER = (
    "\n⚠️ این راهنما توسط هوش مصنوعی تولید شده و ممکنه دقیق ۱۰۰٪ نباشه. "
    "برای مراقبت تخصصی‌تر می‌تونی درخواست ویزیت متخصص گرین‌ویتا رو بزنی."
)


def _format_identification_message(result: PlantIdentificationResult) -> str:
    if not result.parse_succeeded or not result.is_plant:
        return (
            "⚠️ نتونستم گیاه رو به‌درستی شناسایی کنم.\n\n"
            f"{result.preventive_care_tips or result.raw_response}\n\n"
            "لطفاً با یک عکس واضح‌تر از برگ یا کل گیاه دوباره امتحان کن."
        )

    lines: list[str] = [
        f"🌿 <b>{result.persian_name}</b>",
    ]
    if result.scientific_name:
        lines.append(f"🔬 نام علمی: <i>{result.scientific_name}</i>")

    lines.append(f"📊 اطمینان شناسایی: {result.confidence}٪")
    lines.append(f"⚙️ سطح سختی نگهداری: {_DIFFICULTY_LABEL.get(result.difficulty_level, '⚪️ نامشخص')}")

    field_rows = [
        ("☀️ نور", result.light_requirement),
        ("💧 آبیاری", result.watering_schedule),
        ("💦 رطوبت", result.humidity),
        ("🌡 دما", result.temperature),
        ("🪴 خاک مناسب", result.soil_mix),
        ("🌱 کوددهی", result.fertilizer_recommendation),
        ("🏺 توصیه گلدان", result.potting_advice),
        ("🔄 تعویض گلدان", result.repotting_interval),
        ("🧬 سمیت برای حیوانات خانگی", result.toxicity_pets),
        ("👤 سمیت برای انسان", result.toxicity_humans),
    ]
    for label, value in field_rows:
        if value:
            lines.append(f"\n{label}: {value}")

    if result.propagation_methods:
        lines.append("\n🌾 <b>روش‌های تکثیر:</b>")
        lines.extend(f"• {m}" for m in result.propagation_methods)

    if result.common_pests:
        lines.append("\n🐛 <b>آفت‌های رایج:</b>")
        lines.extend(f"• {p}" for p in result.common_pests)

    if result.common_diseases:
        lines.append("\n🩺 <b>بیماری‌های رایج:</b>")
        lines.extend(f"• {d}" for d in result.common_diseases)

    if result.preventive_care_tips:
        lines.append(f"\n🛡 <b>نکات پیشگیرانه:</b>\n{result.preventive_care_tips}")

    lines.append(_DISCLAIMER)
    return "\n".join(lines)


def _format_admin_notification(identification: PlantIdentification, tg_user: TgUser) -> str:
    username_part = f"@{tg_user.username}" if tg_user.username else "بدون یوزرنیم"
    full_name = " ".join(filter(None, [tg_user.first_name, tg_user.last_name])) or "—"

    return (
        "📞 <b>درخواست ویزیت متخصص جدید (پس از شناسایی گیاه)</b>\n\n"
        f"👤 کاربر: {full_name} ({username_part})\n"
        f"🆔 آیدی تلگرام: <code>{tg_user.id}</code>\n\n"
        f"🌿 گیاه شناسایی‌شده: {identification.persian_name}\n"
        f"🔬 نام علمی: {identification.scientific_name or 'نامشخص'}\n"
        f"📊 اطمینان: {identification.confidence}٪\n\n"
        "لطفاً در اسرع وقت با کاربر تماس بگیرید. 🌿"
    )


async def _notify_admins(bot: Bot, identification: PlantIdentification, tg_user: TgUser) -> None:
    settings = get_settings()
    if not settings.admin_ids:
        logger.warning("identification_expert_visit_no_admins_configured", identification_id=identification.id)
        return

    text = _format_admin_notification(identification, tg_user)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("identification_admin_notify_failed", admin_id=admin_id, error=str(exc))


@router.message(Command("identify"))
@router.message(F.text == BTN_IDENTIFY)
async def handle_identify_command(message: Message, state: FSMContext) -> None:
    await state.set_state(IdentificationStates.waiting_photo)
    await message.answer(_IDENTIFY_INTRO_TEXT)


@router.message(IdentificationStates.waiting_photo, F.photo)
async def handle_identification_photo(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    await state.clear()

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    file_id = message.photo[-1].file_id
    status_message = await message.answer("🔎 در حال شناسایی گیاه... چند لحظه صبر کن.")

    identification_repo = PlantIdentificationRepository(session)

    try:
        file_io = await bot.download(file_id)
        image_bytes = file_io.read()

        ai_provider = get_ai_provider()
        result = await identify_plant_image(ai_provider, image_bytes)
    except AIProviderError as exc:
        logger.error("identification_ai_failed", error=str(exc), telegram_user_id=message.from_user.id)
        await status_message.edit_text(
            "😔 در حال حاضر امکان شناسایی گیاه وجود نداره (مشکل ارتباط با سرویس هوش مصنوعی). "
            "چند دقیقه دیگه دوباره امتحان کن."
        )
        return
    except Exception:  # noqa: BLE001
        logger.exception("identification_unexpected_failure", telegram_user_id=message.from_user.id)
        await status_message.edit_text("😔 مشکلی در پردازش عکس پیش اومد. لطفاً دوباره امتحان کن.")
        return

    identification = await identification_repo.create(
        user_id=user.id,
        telegram_file_id=file_id,
        persian_name=result.persian_name,
        scientific_name=result.scientific_name or None,
        confidence=result.confidence,
        difficulty_level=result.difficulty_level,
        light_requirement=result.light_requirement or None,
        watering_schedule=result.watering_schedule or None,
        humidity=result.humidity or None,
        temperature=result.temperature or None,
        soil_mix=result.soil_mix or None,
        fertilizer_recommendation=result.fertilizer_recommendation or None,
        potting_advice=result.potting_advice or None,
        repotting_interval=result.repotting_interval or None,
        propagation_methods="\n".join(result.propagation_methods) or None,
        common_pests="\n".join(result.common_pests) or None,
        common_diseases="\n".join(result.common_diseases) or None,
        toxicity_pets=result.toxicity_pets or None,
        toxicity_humans=result.toxicity_humans or None,
        preventive_care_tips=result.preventive_care_tips or None,
        ai_provider=result.ai_provider,
        raw_response=result.raw_response,
    )

    message_text = _format_identification_message(result)
    keyboard = (
        get_identification_result_keyboard(identification.id)
        if result.parse_succeeded and result.is_plant
        else None
    )
    await status_message.edit_text(message_text, reply_markup=keyboard)


@router.message(IdentificationStates.waiting_photo)
async def handle_identification_waiting_non_photo(message: Message) -> None:
    await message.answer(_ASK_FOR_PHOTO_TEXT)


@router.callback_query(DiagnoseFromIdentificationCallback.filter())
async def handle_diagnose_from_identification(
    callback: CallbackQuery,
    callback_data: DiagnoseFromIdentificationCallback,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    identification_repo = PlantIdentificationRepository(session)
    identification = await identification_repo.get_by_id(callback_data.identification_id)

    if not identification:
        await callback.answer("این درخواست دیگر معتبر نیست.", show_alert=True)
        return

    await state.update_data(
        diagnosis_file_id=identification.telegram_file_id,
        plant_name=identification.persian_name,
    )
    await state.set_state(DiagnosisStates.waiting_plant_details)

    await callback.answer()
    await callback.message.answer(
        f"🩺 حله، همون عکس «{identification.persian_name}» رو برای تشخیص بیماری بررسی می‌کنم.\n\n"
        "📝 توضیح بیشتری درباره‌ی وضعیت گیاه داری؟ (اگه نداری، دکمه‌ی زیر رو بزن)",
        reply_markup=get_skip_details_keyboard(),
    )


@router.callback_query(IdentificationExpertVisitCallback.filter())
async def handle_identification_expert_visit(
    callback: CallbackQuery,
    callback_data: IdentificationExpertVisitCallback,
    session: AsyncSession,
) -> None:
    identification_repo = PlantIdentificationRepository(session)
    identification = await identification_repo.get_by_id(callback_data.identification_id)

    if not identification:
        await callback.answer("این درخواست دیگر معتبر نیست.", show_alert=True)
        return

    if identification.expert_visit_requested:
        await callback.answer("درخواست شما قبلاً ثبت شده. کارشناسان به‌زودی تماس می‌گیرند. 🌿", show_alert=True)
        return

    await identification_repo.update(identification, expert_visit_requested=True)
    await _notify_admins(callback.bot, identification, callback.from_user)

    await callback.answer("درخواست شما ثبت شد ✅", show_alert=True)
    await callback.message.answer(
        "📞 درخواست ویزیت متخصص شما برای کلینیک گیاه‌پزشکی گرین‌ویتا ثبت شد. "
        "کارشناسان ما به‌زودی از طریق همین تلگرام باهاتون تماس می‌گیرن. 🌿"
    )
