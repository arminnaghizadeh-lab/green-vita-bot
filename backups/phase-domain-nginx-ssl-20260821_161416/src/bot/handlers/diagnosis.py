"""
هندلر تشخیص بیماری گیاه از روی عکس.

فلو:
1. کاربر عکس گیاه را می‌فرستد.
2. ازش اسم/نوع گیاه پرسیده می‌شود.
3. ازش توضیح تکمیلی (اختیاری) پرسیده می‌شود.
4. عکس + پاسخ‌های کاربر به AI Provider فعال (پیش‌فرض Claude) فرستاده می‌شود.
5. نتیجه (تشخیص + توصیه درمانی) پارس، ذخیره و برای کاربر ارسال می‌شود
   همراه با دکمه‌ی «درخواست ویزیت متخصص گرین‌ویتا».
6. با زدن آن دکمه، به همه‌ی ادمین‌های تنظیم‌شده در BOT_ADMIN_IDS اطلاع داده می‌شود.
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.diagnosis import DiagnosisResult, diagnose_plant_image
from src.ai.factory import get_ai_provider
from src.bot.keyboards import (
    ExpertVisitCallback,
    SkipDetailsCallback,
    get_expert_visit_keyboard,
    get_skip_details_keyboard,
)
from src.bot.keyboards.main_menu import BTN_DIAGNOSE
from src.bot.states import DiagnosisStates
from src.core.config import get_settings
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger
from src.db.models.diagnosis import Diagnosis, DiagnosisSeverity
from src.repositories.diagnosis_repository import DiagnosisRepository
from src.repositories.user_repository import UserRepository

logger = get_logger("bot.handlers.diagnosis")

router = Router(name="diagnosis")

_SEVERITY_EMOJI = {
    DiagnosisSeverity.NONE: "🟢",
    DiagnosisSeverity.MILD: "🟡",
    DiagnosisSeverity.MODERATE: "🟠",
    DiagnosisSeverity.SEVERE: "🔴",
    DiagnosisSeverity.UNKNOWN: "⚪️",
}

DIAGNOSIS_INTRO_TEXT = (
    "📷 یک عکس واضح و نزدیک از برگ، ساقه یا قسمت آسیب‌دیده‌ی گیاه بفرست "
    "تا وضعیت سلامتش رو بررسی کنم."
)

_ASK_PLANT_NAME_TEXT = (
    "🌱 اسم یا نوع این گیاه رو می‌دونی؟\n"
    "(مثلاً: مونستِرا، پتوس، ارکیده...)\n"
    "اگه نمی‌دونی، همینجا بنویس «نمی‌دونم»."
)

_ASK_PLANT_DETAILS_TEXT = (
    "📝 توضیح بیشتری درباره‌ی وضعیت گیاه داری؟\n"
    "(مثلاً از کِی این علائم رو دیدی، کجا نگهداریش می‌کنی، چند وقت یک‌بار آبش می‌دی...)\n"
    "اگه توضیحی نداری، دکمه‌ی زیر رو بزن."
)


def _format_diagnosis_message(result: DiagnosisResult, *, plant_name: str | None) -> str:
    if not result.parse_succeeded:
        return (
            "⚠️ نتونستم تحلیل رو در قالب استاندارد دریافت کنم، ولی این پاسخ خام هوش مصنوعی است:\n\n"
            f"{result.treatment}\n\n"
            "لطفاً دوباره با یک عکس واضح‌تر امتحان کن."
        )

    emoji = _SEVERITY_EMOJI.get(result.severity, "⚪️")
    lines: list[str] = []

    if plant_name:
        lines.append(f"🌱 گیاه: <b>{plant_name}</b>")

    if result.is_healthy:
        lines.append("✅ <b>گیاه شما سالم به نظر می‌رسد!</b>")
        lines.append(f"📊 میزان اطمینان: {result.confidence}٪")
        if result.symptoms:
            lines.append("\n🔍 <b>موارد بررسی‌شده:</b>")
            lines.extend(f"• {s}" for s in result.symptoms)
        if result.prevention:
            lines.append(f"\n🛡 <b>نکات نگهداری:</b>\n{result.prevention}")
        lines.append(
            "\n⚠️ این تحلیل توسط هوش مصنوعی انجام شده و جایگزین ویزیت تخصصی نیست."
        )
        return "\n".join(lines)

    # زنجیره‌ی اصلی: ۱) تشخیص  ←  ۲) علت  ←  ۳) درمان
    lines.append(f"1️⃣ <b>تشخیص:</b> {emoji} {result.disease_name}")
    lines.append(f"📊 میزان اطمینان تشخیص: {result.confidence}٪")
    if result.symptoms:
        lines.append("\n🔍 <b>علائم مشاهده‌شده:</b>")
        lines.extend(f"• {s}" for s in result.symptoms)

    lines.append("\n⬇️")
    lines.append(f"\n2️⃣ <b>علت:</b>\n{result.cause or 'علت مشخصی گزارش نشده است.'}")

    lines.append("\n⬇️")
    lines.append(f"\n3️⃣ <b>درمان:</b>\n{result.treatment or 'توصیه درمانی مشخصی گزارش نشده است.'}")

    if result.prevention:
        lines.append(f"\n🛡 <b>پیشگیری از تکرار:</b>\n{result.prevention}")

    lines.append(
        "\n⚠️ این تحلیل توسط هوش مصنوعی انجام شده و جایگزین ویزیت تخصصی نیست."
    )

    return "\n".join(lines)


def _format_admin_notification(diagnosis: Diagnosis, tg_user: TgUser) -> str:
    username_part = f"@{tg_user.username}" if tg_user.username else "بدون یوزرنیم"
    full_name = " ".join(filter(None, [tg_user.first_name, tg_user.last_name])) or "—"

    return (
        "📞 <b>درخواست ویزیت متخصص جدید</b>\n\n"
        f"👤 کاربر: {full_name} ({username_part})\n"
        f"🆔 آیدی تلگرام: <code>{tg_user.id}</code>\n\n"
        f"🌱 گیاه: {diagnosis.plant_name_input or 'نامشخص'}\n"
        f"🩺 تشخیص: {diagnosis.disease_name}\n"
        f"📊 شدت: {diagnosis.severity.value} | اطمینان: {diagnosis.confidence}٪\n\n"
        "لطفاً در اسرع وقت با کاربر تماس بگیرید. 🌿"
    )


async def _notify_admins_of_expert_visit(bot: Bot, diagnosis: Diagnosis, tg_user: TgUser) -> None:
    settings = get_settings()
    if not settings.admin_ids:
        logger.warning("expert_visit_no_admins_configured", diagnosis_id=diagnosis.id)
        return

    text = _format_admin_notification(diagnosis, tg_user)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("expert_visit_admin_notify_failed", admin_id=admin_id, error=str(exc))


async def _run_diagnosis_and_reply(
    *,
    bot: Bot,
    session: AsyncSession,
    user_id: int,
    telegram_user_id: int,
    file_id: str,
    plant_name: str | None,
    user_notes: str | None,
    status_message: Message,
) -> None:
    diagnosis_repo = DiagnosisRepository(session)

    try:
        file_io = await bot.download(file_id)
        image_bytes = file_io.read()

        ai_provider = get_ai_provider()
        result = await diagnose_plant_image(
            ai_provider, image_bytes, plant_name=plant_name, user_notes=user_notes
        )
    except AIProviderError as exc:
        logger.error("diagnosis_ai_failed", error=str(exc), telegram_user_id=telegram_user_id)
        await status_message.edit_text(
            "😔 در حال حاضر امکان تحلیل عکس وجود نداره (مشکل ارتباط با سرویس هوش مصنوعی). "
            "چند دقیقه دیگه دوباره امتحان کن."
        )
        return
    except Exception:  # noqa: BLE001
        logger.exception("diagnosis_unexpected_failure", telegram_user_id=telegram_user_id)
        await status_message.edit_text("😔 مشکلی در پردازش عکس پیش اومد. لطفاً دوباره امتحان کن.")
        return

    diagnosis = await diagnosis_repo.create(
        user_id=user_id,
        plant_id=None,
        telegram_file_id=file_id,
        plant_name_input=plant_name,
        user_notes=user_notes,
        is_healthy=result.is_healthy,
        disease_name=result.disease_name,
        severity=result.severity,
        confidence=result.confidence,
        symptoms="\n".join(result.symptoms) if result.symptoms else None,
        cause=result.cause or None,
        treatment=result.treatment or None,
        prevention=result.prevention or None,
        ai_provider=result.ai_provider,
        raw_response=result.raw_response,
    )

    message_text = _format_diagnosis_message(result, plant_name=plant_name)
    keyboard = get_expert_visit_keyboard(diagnosis.id) if result.parse_succeeded else None

    await status_message.edit_text(message_text, reply_markup=keyboard)


@router.message(Command("diagnose"))
@router.message(F.text == BTN_DIAGNOSE)
async def handle_diagnose_command(message: Message) -> None:
    await message.answer(DIAGNOSIS_INTRO_TEXT)


@router.message(F.photo)
async def handle_photo_received(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user_repo = UserRepository(session)
    await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    largest_photo = message.photo[-1]
    await state.update_data(diagnosis_file_id=largest_photo.file_id)
    await state.set_state(DiagnosisStates.waiting_plant_name)
    await message.answer(_ASK_PLANT_NAME_TEXT)


@router.message(DiagnosisStates.waiting_plant_name, F.text)
async def handle_plant_name_received(message: Message, state: FSMContext) -> None:
    plant_name = message.text.strip()
    if plant_name in {"نمی‌دونم", "نمیدونم", "-"}:
        plant_name = None

    await state.update_data(plant_name=plant_name)
    await state.set_state(DiagnosisStates.waiting_plant_details)
    await message.answer(_ASK_PLANT_DETAILS_TEXT, reply_markup=get_skip_details_keyboard())


@router.message(DiagnosisStates.waiting_plant_details, F.text)
async def handle_plant_details_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()

    file_id = data.get("diagnosis_file_id")
    if not file_id:
        await message.answer("این درخواست منقضی شده. یک عکس جدید بفرست.")
        return

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(telegram_id=message.from_user.id)

    status_message = await message.answer("🔎 در حال تحلیل عکس... چند لحظه صبر کن.")
    await _run_diagnosis_and_reply(
        bot=message.bot,
        session=session,
        user_id=user.id,
        telegram_user_id=message.from_user.id,
        file_id=file_id,
        plant_name=data.get("plant_name"),
        user_notes=message.text.strip(),
        status_message=status_message,
    )


@router.callback_query(DiagnosisStates.waiting_plant_details, SkipDetailsCallback.filter())
async def handle_skip_details(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()

    file_id = data.get("diagnosis_file_id")
    await callback.answer()

    if not file_id:
        await callback.message.edit_text("این درخواست منقضی شده. یک عکس جدید بفرست.")
        return

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(telegram_id=callback.from_user.id)

    await callback.message.edit_text("🔎 در حال تحلیل عکس... چند لحظه صبر کن.")
    await _run_diagnosis_and_reply(
        bot=callback.bot,
        session=session,
        user_id=user.id,
        telegram_user_id=callback.from_user.id,
        file_id=file_id,
        plant_name=data.get("plant_name"),
        user_notes=None,
        status_message=callback.message,
    )


@router.callback_query(ExpertVisitCallback.filter())
async def handle_expert_visit_request(
    callback: CallbackQuery, callback_data: ExpertVisitCallback, session: AsyncSession
) -> None:
    diagnosis_repo = DiagnosisRepository(session)
    diagnosis = await diagnosis_repo.get_by_id(callback_data.diagnosis_id)

    if not diagnosis:
        await callback.answer("این درخواست دیگر معتبر نیست.", show_alert=True)
        return

    if diagnosis.expert_visit_requested:
        await callback.answer("درخواست شما قبلاً ثبت شده. کارشناسان به‌زودی تماس می‌گیرند. 🌿", show_alert=True)
        return

    await diagnosis_repo.update(diagnosis, expert_visit_requested=True)
    await _notify_admins_of_expert_visit(callback.bot, diagnosis, callback.from_user)

    await callback.answer("درخواست شما ثبت شد ✅", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "📞 درخواست ویزیت متخصص شما برای کلینیک گیاه‌پزشکی گرین‌ویتا ثبت شد. "
        "کارشناسان ما به‌زودی از طریق همین تلگرام باهاتون تماس می‌گیرن. 🌿"
    )
