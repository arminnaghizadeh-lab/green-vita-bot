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
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User as TgUser,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.diagnosis import DiagnosisResult, diagnose_plant_image
from src.ai.factory import get_ai_provider
from src.bot.keyboards import (
    ExpertVisitCallback,
    SkipDetailsCallback,
    get_expert_visit_keyboard,
    get_skip_details_keyboard,
)
from src.bot.keyboards.main_menu import (
    BTN_DIAGNOSE,
    BTN_EXPERT_VISIT,
    get_main_menu_keyboard,
)
from src.bot.states import DiagnosisStates, ExpertVisitStates
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


def _format_admin_notification(
    diagnosis: Diagnosis,
    tg_user: TgUser,
    *,
    contact_name: str,
    contact_phone: str,
) -> str:
    username_part = f"@{tg_user.username}" if tg_user.username else "بدون یوزرنیم"

    return (
        "📞 <b>درخواست ویزیت متخصص جدید</b>\n\n"
        f"👤 نام و نام خانوادگی: {contact_name}\n"
        f"📱 شماره تماس: <code>{contact_phone}</code>\n"
        f"👤 تلگرام: {username_part}\n"
        f"🆔 آیدی تلگرام: <code>{tg_user.id}</code>\n\n"
        f"🌱 گیاه: {diagnosis.plant_name_input or 'نامشخص'}\n"
        f"🩺 تشخیص: {diagnosis.disease_name}\n"
        f"📊 شدت: {diagnosis.severity.value} | اطمینان: {diagnosis.confidence}٪\n\n"
        "لطفاً در اسرع وقت با کاربر تماس بگیرید. 🌿"
    )


async def _notify_admins_of_expert_visit(
    bot: Bot,
    diagnosis: Diagnosis,
    tg_user: TgUser,
    *,
    contact_name: str,
    contact_phone: str,
) -> None:
    settings = get_settings()

    if not settings.admin_ids:
        logger.warning(
            "expert_visit_no_admins_configured",
            diagnosis_id=diagnosis.id,
        )
        return

    text = _format_admin_notification(
        diagnosis,
        tg_user,
        contact_name=contact_name,
        contact_phone=contact_phone,
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
            )
            logger.info(
                "expert_visit_admin_notified",
                diagnosis_id=diagnosis.id,
                admin_id=admin_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "expert_visit_admin_notify_failed",
                diagnosis_id=diagnosis.id,
                admin_id=admin_id,
                error=str(exc),
            )


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

    # Expert Visit must remain available for every successfully persisted
    # diagnosis result, including cases where AI parsing was not successful.
    keyboard = get_expert_visit_keyboard(diagnosis.id)

    await status_message.edit_text(message_text, reply_markup=keyboard)


@router.message(Command("diagnose"))
@router.message(F.text == BTN_DIAGNOSE)
async def handle_diagnose_command(message: Message) -> None:
    await message.answer(DIAGNOSIS_INTRO_TEXT)


@router.message(F.text == BTN_EXPERT_VISIT)
async def handle_direct_expert_visit(
    message: Message,
    state: FSMContext,
) -> None:
    """
    شروع درخواست مستقیم ویزیت متخصص.
    ابتدا نام و سپس شماره تلفن کاربر دریافت می‌شود.
    ثبت نهایی بعد از تکمیل اطلاعات تماس انجام خواهد شد.
    """
    await state.clear()
    await state.update_data(
        expert_visit_source="direct",
        expert_visit_id=None,
    )
    await state.set_state(ExpertVisitStates.waiting_name)

    try:
        _debug_state = await state.get_state()
        _debug_data = await state.get_data()
        logger.info(
            "expert_visit_start_trace",
            telegram_user_id=message.from_user.id,
            chat_id=message.chat.id,
            state=_debug_state,
            data=_debug_data,
        )
    except Exception:
        logger.exception("expert_visit_start_trace_failed")

    await message.answer(
        "📞 <b>درخواست ویزیت متخصص</b>\n\n"
        "لطفاً نام و نام خانوادگی خودت رو وارد کن:"
    )


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
    callback: CallbackQuery,
    callback_data: ExpertVisitCallback,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.clear()
    await state.update_data(
        expert_visit_source="diagnosis",
        expert_visit_id=callback_data.diagnosis_id,
    )
    await state.set_state(ExpertVisitStates.waiting_name)

    await callback.message.answer(
        "📞 <b>درخواست ویزیت متخصص</b>\n\n"
        "لطفاً نام و نام خانوادگی خودت رو وارد کن:"
    )


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if phone.startswith("00"):
        phone = "+" + phone[2:]

    return phone


def _is_valid_phone(phone: str) -> bool:
    normalized = _normalize_phone(phone)
    digits = normalized[1:] if normalized.startswith("+") else normalized
    return digits.isdigit() and 8 <= len(digits) <= 15


async def _finish_expert_visit(
    *,
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    name: str,
    phone: str,
) -> None:
    data = await state.get_data()
    source = data.get("expert_visit_source")
    record_id = data.get("expert_visit_id")

    user_repo = UserRepository(session)

    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
    )

    name_parts = name.strip().split(maxsplit=1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else None

    phone = _normalize_phone(phone)

    await user_repo.update_contact(
        user,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
    )

    if source == "direct":
        diagnosis_repo = DiagnosisRepository(session)

        diagnosis = await diagnosis_repo.create(
            user_id=user.id,
            plant_id=None,
            telegram_file_id="direct_expert_visit",
            plant_name_input=None,
            user_notes=None,
            is_healthy=False,
            disease_name="درخواست ویزیت متخصص",
            severity=DiagnosisSeverity.UNKNOWN,
            confidence=0,
            symptoms=None,
            cause=None,
            treatment=None,
            prevention=None,
            ai_provider="manual",
            raw_response=None,
            expert_visit_requested=True,
        )

        await _notify_admins_of_expert_visit(
            message.bot,
            diagnosis,
            message.from_user,
            contact_name=name,
            contact_phone=phone,
        )

    elif source == "diagnosis":
        diagnosis_repo = DiagnosisRepository(session)
        diagnosis = await diagnosis_repo.get_by_id(record_id)

        if not diagnosis:
            await state.clear()
            await message.answer(
                "این درخواست دیگر معتبر نیست. لطفاً دوباره درخواست ویزیت بده."
            )
            return

        if not diagnosis.expert_visit_requested:
            await diagnosis_repo.update(
                diagnosis,
                expert_visit_requested=True,
            )

        await _notify_admins_of_expert_visit(
            message.bot,
            diagnosis,
            message.from_user,
            contact_name=name,
            contact_phone=phone,
        )

    elif source == "identification":
        from src.repositories.plant_identification_repository import (
            PlantIdentificationRepository,
        )
        from src.bot.handlers.identification import _notify_admins

        identification_repo = PlantIdentificationRepository(session)
        identification = await identification_repo.get_by_id(record_id)

        if not identification:
            await state.clear()
            await message.answer(
                "این درخواست دیگر معتبر نیست. لطفاً دوباره درخواست ویزیت بده."
            )
            return

        if not identification.expert_visit_requested:
            await identification_repo.update(
                identification,
                expert_visit_requested=True,
            )

        await _notify_admins(
            message.bot,
            identification,
            message.from_user,
        )

    else:
        await state.clear()
        await message.answer(
            "درخواست ویزیت نامعتبر است. لطفاً دوباره از منوی اصلی اقدام کن."
        )
        return

    await state.clear()

    # Remove the temporary "send phone number" keyboard first.
    await message.answer(
        "✅ <b>درخواست ویزیت متخصص ثبت شد.</b>\n\n"
        "نام و شماره تماس شما برای کارشناسان کلینیک ارسال شد.\n"
        "کارشناسان گرین‌ویتا در اولین فرصت با شما تماس می‌گیرند. 🌿",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Restore the permanent main menu.
    await message.answer(
        "🏠 <b>منوی اصلی</b>\n\n"
        "از گزینه‌های زیر می‌تونی استفاده کنی:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(ExpertVisitStates.waiting_name, F.text)
async def handle_expert_visit_name(
    message: Message,
    state: FSMContext,
) -> None:
    try:
        _debug_state = await state.get_state()
        _debug_data = await state.get_data()
        logger.info(
            "expert_visit_name_trace",
            telegram_user_id=message.from_user.id,
            chat_id=message.chat.id,
            incoming_text=message.text,
            state=_debug_state,
            data=_debug_data,
        )
    except Exception:
        logger.exception("expert_visit_name_trace_failed")

    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "لطفاً نام و نام خانوادگی معتبر وارد کن:"
        )
        return

    await state.update_data(expert_visit_name=name)
    await state.set_state(ExpertVisitStates.waiting_phone)

    try:
        _debug_state = await state.get_state()
        _debug_data = await state.get_data()
        logger.info(
            "expert_visit_waiting_phone_trace",
            telegram_user_id=message.from_user.id,
            chat_id=message.chat.id,
            state=_debug_state,
            data=_debug_data,
        )
    except Exception:
        logger.exception("expert_visit_waiting_phone_trace_failed")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 ارسال شماره تلفن",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await message.answer(
        "📱 حالا شماره تلفنت رو ارسال کن.\n\n"
        "می‌تونی روی دکمه‌ی «ارسال شماره تلفن» بزنی "
        "یا شماره رو دستی وارد کنی.",
        reply_markup=keyboard,
    )


@router.message(ExpertVisitStates.waiting_phone, F.contact)
async def handle_expert_visit_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    # Telegram contact updates are handled directly.
    # Do not reject the update solely because the Redis FSM state
    # is missing/stale after a restart or an old keyboard interaction.

    try:
        _debug_state = await state.get_state()
        _debug_data = await state.get_data()
        logger.info(
            "expert_visit_contact_trace",
            telegram_user_id=message.from_user.id,
            chat_id=message.chat.id,
            contact_user_id=message.contact.user_id,
            contact_phone=message.contact.phone_number,
            state=_debug_state,
            data=_debug_data,
        )
    except Exception:
        logger.exception("expert_visit_contact_trace_failed")

    contact = message.contact

    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ لطفاً شماره تلفن خودت رو ارسال کن، نه شماره شخص دیگری.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return

    data = await state.get_data()
    name = data.get("expert_visit_name")

    # اگر Contact مربوط به یک درخواست قدیمی/منقضی باشد و FSM دیگر
    # اطلاعات نام را نداشته باشد، نباید کاربر روی کیبورد قدیمی گیر کند.
    # Contact را ذخیره نمی‌کنیم؛ فقط کیبورد قدیمی را حذف و منوی اصلی را برمی‌گردانیم.
    if not name:
        # The user may still have Telegram's old request_contact keyboard
        # visible even though the Redis FSM state is already gone.
        # Explicitly remove it first, then restore the permanent main menu.
        await state.clear()

        await message.answer(
            "ℹ️ درخواست قبلی ویزیت منقضی شده است.",
            reply_markup=ReplyKeyboardRemove(),
        )

        await message.answer(
            "🏠 <b>منوی اصلی</b>\n\n"
            "از گزینه‌های زیر می‌تونی استفاده کنی:",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await _finish_expert_visit(
        message=message,
        session=session,
        state=state,
        name=name,
        phone=contact.phone_number,
    )


@router.message(ExpertVisitStates.waiting_phone, F.text)
async def handle_expert_visit_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        _debug_state = await state.get_state()
        _debug_data = await state.get_data()
        logger.info(
            "expert_visit_manual_phone_trace",
            telegram_user_id=message.from_user.id,
            chat_id=message.chat.id,
            incoming_text=message.text,
            state=_debug_state,
            data=_debug_data,
        )
    except Exception:
        logger.exception("expert_visit_manual_phone_trace_failed")

    phone = message.text.strip()

    if not _is_valid_phone(phone):
        await message.answer(
            "⚠️ شماره تلفن معتبر نیست.\n\n"
            "لطفاً شماره را دوباره وارد کن، مثلاً:\n"
            "<code>09121234567</code>"
        )
        return

    data = await state.get_data()
    name = data.get("expert_visit_name")

    if not name:
        await state.clear()
        await message.answer(
            "اطلاعات درخواست ناقص شد. لطفاً دوباره درخواست ویزیت بده."
        )
        return

    await _finish_expert_visit(
        message=message,
        session=session,
        state=state,
        name=name,
        phone=phone,
    )
