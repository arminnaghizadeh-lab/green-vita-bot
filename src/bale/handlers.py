"""Handlers and reply keyboard for the Green Vita Bale bot."""

from __future__ import annotations

from typing import Any

from src.db.session import session_scope
from src.admin.services.push import send_push
from src.admin.services.badge import get_admin_badge_count
from src.ai.diagnosis import diagnose_plant_image
from src.ai.plant_identification import identify_plant_image
from src.db.models.plant_identification import PlantIdentification, DifficultyLevel
from src.repositories.plant_identification_repository import PlantIdentificationRepository
from src.ai.factory import get_ai_provider
from src.core.exceptions import AIProviderError
from src.core.logging import get_logger
from src.db.models.diagnosis import DiagnosisSeverity
from src.repositories.diagnosis_repository import DiagnosisRepository
from src.repositories.plant_repository import PlantRepository
from src.repositories.user_repository import UserRepository
from src.bale.state import clear_state, get_data, get_state, set_state, update_data

logger = get_logger("bale.handlers")


WELCOME_TEXT = (
    "🌿 به دستیار هوشمند گرین ویتا خوش آمدید!\n\n"
    "من دستیار هوشمند کلینیک گیاه‌پزشکی گرین‌ویتا هستم.\n\n"
    "از منوی پایین می‌توانید بخش موردنظر را انتخاب کنید."
)

HELP_TEXT = (
    "🆘 راهنمای استفاده از گرین ویتا\n\n"
    "🩺 تشخیص بیماری\n"
    "تشخیص بیماری گیاه از روی عکس.\n\n"
    "🔍 شناسایی گیاه\n"
    "شناسایی گونه گیاه از روی عکس.\n\n"
    "🌱 گیاهان من\n"
    "مشاهده پرونده گیاهان ثبت‌شده.\n\n"
    "📞 درخواست ویزیت متخصص\n"
    "درخواست بررسی توسط متخصص.\n\n"
    "برای بازگشت به منوی اصلی، «🏠 شروع» را انتخاب کنید."
)

ABOUT_TEXT = (
    "🌿 کلینیک گیاهپزشکی گرین ویتا\n\n"
    "گرین ویتا یک کلینیک تخصصی در زمینه گیاهان و گیاه‌پزشکی است "
    "که با هدف کمک به نگهداری بهتر و درمان اصولی گیاهان فعالیت می‌کند.\n\n"
    "📞 شماره تماس: ۰۹۱۲۸۱۱۱۰۵۸"
)

UNKNOWN_TEXT = (
    "🌿 پیام شما دریافت شد.\n\n"
    "از منوی پایین یکی از گزینه‌ها را انتخاب کنید."
)


MAIN_MENU = {
    "inline_keyboard": [
        [
            {"text": "🩺 تشخیص بیماری", "callback_data": "diagnose"},
            {"text": "🔍 شناسایی گیاه", "callback_data": "identify"},
        ],
        [
            {"text": "🌱 گیاهان من", "callback_data": "plants"},
            {"text": "📞 درخواست ویزیت متخصص", "callback_data": "visit"},
        ],
        [
            {"text": "ℹ️ درباره ما", "callback_data": "about"},
            {"text": "🆘 راهنما", "callback_data": "help"},
        ],
    ]
}

BACK_HOME_MENU = {
    "inline_keyboard": [
        [
            {"text": "🏠 منوی اصلی", "callback_data": "home"},
        ]
    ]
}


BALE_ABOUT_MENU = {
    "inline_keyboard": [
        [
            {
                "text": "📩 ارسال پیام در واتساپ",
                "url": "https://wa.me/message/3TYFRDAI5SAMM1",
            }
        ],
        [
            {
                "text": "📷 صفحه اینستاگرام گرین ویتا",
                "url": "https://www.instagram.com/greenvita_clinic/",
            }
        ],
        [
            {
                "text": "📍 آدرس ما",
                "url": "https://nshn.ir/rbvZlRPxVSMS",
            }
        ],
        [
            {
                "text": "🌐 سایت گرین ویتا",
                "url": "https://Greenvitaclinic.ir",
            }
        ],
        [
            {
                "text": "🤖 دستیار هوشمند تلگرام",
                "url": "https://t.me/GreenVita_AI_Bot",
            }
        ],
        [
            {
                "text": "🏠 منوی اصلی",
                "callback_data": "home",
            }
        ],
    ]
}


def _bale_phone_request_markup() -> dict[str, Any]:
    """Reply keyboard for direct Bale contact sharing."""
    return {
        "keyboard": [
            [
                {
                    "text": "📱 ارسال شماره تلفن",
                    "request_contact": True,
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _bale_remove_phone_keyboard_markup() -> dict[str, Any]:
    """Remove phone reply keyboard while keeping the Home inline button."""
    return {
        "remove_keyboard": True,
        "inline_keyboard": [
            [
                {
                    "text": "🏠 منوی اصلی",
                    "callback_data": "home",
                }
            ]
        ],
    }



def _command_name(text: str) -> str:
    first = text.strip().split(maxsplit=1)[0] if text.strip() else ""
    return first.split("@", 1)[0].lower()


async def _register_user(message: dict[str, Any]) -> tuple[int, bool]:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    async with session_scope() as session:
        repo = UserRepository(session)

        user, created = await repo.get_or_create_bale(
            int(bale_id),
            username=sender.get("username"),
            first_name=sender.get("first_name"),
            last_name=sender.get("last_name"),
            language_code=sender.get("language_code"),
        )

        return user.id, created


async def _send_menu(
    client: Any,
    *,
    chat_id: int,
    text: str,
) -> None:
    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": MAIN_MENU,
        },
    )


async def handle_start(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)
    await _send_menu(
        client,
        chat_id=chat_id,
        text=WELCOME_TEXT,
    )


async def handle_help(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)
    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": HELP_TEXT,
            "reply_markup": BACK_HOME_MENU,
        },
    )


async def handle_about(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)
    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": ABOUT_TEXT,
            "reply_markup": BALE_ABOUT_MENU,
        },
    )


async def handle_plants(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)

    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    async with session_scope() as session:
        user_repo = UserRepository(session)
        plant_repo = PlantRepository(session)

        user, _ = await user_repo.get_or_create_bale(
            int(bale_id),
            username=sender.get("username"),
            first_name=sender.get("first_name"),
            last_name=sender.get("last_name"),
            language_code=sender.get("language_code"),
        )

        plants = await plant_repo.list_by_owner(user.id)

    if not plants:
        text = (
            "🌱 <b>گیاهان من</b>\n\n"
            "هنوز هیچ گیاهی ثبت نکردی.\n"
            "با دکمه زیر اولین پرونده گیاهت را بساز."
        )
    else:
        lines = [
            "🌱 <b>گیاهان من</b>",
            "",
            "برای مشاهده پرونده، روی گیاه موردنظر بزن:",
        ]

        for plant in plants:
            species = plant.species or "گونه نامشخص"
            lines.append(
                f"🌱 {plant.name} — {species}"
            )

        text = "\n".join(lines)

    keyboard = [
        [
            {
                "text": "➕ افزودن گیاه جدید",
                "callback_data": "plant_add",
            }
        ]
    ]

    for plant in plants:
        keyboard.append(
            [
                {
                    "text": f"🌿 {plant.name}",
                    "callback_data": f"plant_view:{plant.id}",
                }
            ]
        )

    keyboard.append(
        [
            {
                "text": "🏠 منوی اصلی",
                "callback_data": "home",
            }
        ]
    )

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": keyboard,
            },
        },
    )


async def _get_bale_owned_plant(
    bale_id: int,
    plant_id: int,
):
    async with session_scope() as session:
        user_repo = UserRepository(session)
        plant_repo = PlantRepository(session)

        user = await user_repo.get_by_bale_id(bale_id)
        if user is None:
            return None

        plant = await plant_repo.get_by_id(plant_id)

        if plant is None or plant.owner_id != user.id:
            return None

        return plant


async def _handle_bale_plant_view(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
    plant_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        return

    plant = await _get_bale_owned_plant(
        int(bale_id),
        plant_id,
    )

    if plant is None:
        await client.call(
            "sendMessage",
            json={
                "chat_id": chat_id,
                "text": "⚠️ این گیاه پیدا نشد یا متعلق به شما نیست.",
            },
        )
        return

    status_labels = {
        "healthy": "🟢 سالم",
        "sick": "🔴 بیمار",
        "under_treatment": "🟡 در حال درمان",
        "recovered": "✅ بهبودیافته",
        "unknown": "⚪️ نامشخص",
    }

    health_value = getattr(
        plant.health_status,
        "value",
        str(plant.health_status),
    )

    text = (
        f"🌱 <b>{plant.name}</b>\\n\\n"
        f"🔍 نوع/گونه: {plant.species or 'نامشخص'}\\n"
        f"📊 وضعیت سلامت: {status_labels.get(health_value, '⚪️ نامشخص')}"
    )

    if plant.notes:
        text += f"\\n\\n📝 یادداشت: {plant.notes}"

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🗑 حذف گیاه",
                            "callback_data": f"plant_delete:{plant.id}",
                        }
                    ],
                    [
                        {
                            "text": "🌱 بازگشت به گیاهان من",
                            "callback_data": "plants",
                        }
                    ],
                    [
                        {
                            "text": "🏠 منوی اصلی",
                            "callback_data": "home",
                        }
                    ],
                ]
            },
        },
    )


async def _handle_bale_plant_delete_request(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
    plant_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        return

    plant = await _get_bale_owned_plant(
        int(bale_id),
        plant_id,
    )

    if plant is None:
        await client.call(
            "sendMessage",
            json={
                "chat_id": chat_id,
                "text": "⚠️ این گیاه پیدا نشد یا متعلق به شما نیست.",
            },
        )
        return

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                f"⚠️ مطمئنی می‌خوای پرونده «{plant.name}» را حذف کنی؟\\n\\n"
                "این کار قابل برگشت نیست."
            ),
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ بله، حذف کن",
                            "callback_data": f"plant_delete_confirm:{plant.id}",
                        }
                    ],
                    [
                        {
                            "text": "❌ لغو",
                            "callback_data": f"plant_view:{plant.id}",
                        }
                    ],
                ]
            },
        },
    )


async def _handle_bale_plant_delete_confirm(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
    plant_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        return

    async with session_scope() as session:
        user_repo = UserRepository(session)
        plant_repo = PlantRepository(session)

        user = await user_repo.get_by_bale_id(int(bale_id))
        if user is None:
            return

        plant = await plant_repo.get_by_id(plant_id)

        if plant is None or plant.owner_id != user.id:
            await client.call(
                "sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "⚠️ این گیاه پیدا نشد.",
                },
            )
            return

        plant_name = plant.name
        await plant_repo.delete(plant)

        plants = await plant_repo.list_by_owner(user.id)

    lines = [
        f"🗑 پرونده «{plant_name}» حذف شد.",
        "",
    ]

    if plants:
        lines.append("🌱 <b>گیاهان من</b>")
        lines.append("")
        lines.append("گیاه موردنظر را انتخاب کن:")
    else:
        lines.append("هنوز هیچ گیاهی ثبت نکردی.")

    keyboard = [
        [
            {
                "text": "➕ افزودن گیاه جدید",
                "callback_data": "plant_add",
            }
        ]
    ]

    for plant in plants:
        keyboard.append(
            [
                {
                    "text": f"🌿 {plant.name}",
                    "callback_data": f"plant_view:{plant.id}",
                }
            ]
        )

    keyboard.append(
        [
            {
                "text": "🏠 منوی اصلی",
                "callback_data": "home",
            }
        ]
    )

    await clear_state(int(bale_id))

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": "\\n".join(lines),
            "reply_markup": {
                "inline_keyboard": keyboard,
            },
        },
    )


async def handle_diagnose(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)

    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    await set_state(int(bale_id), "diagnosis_waiting_photo")

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                "🩺 <b>تشخیص بیماری گیاه</b>\n\n"
                "📷 یک عکس واضح و نزدیک از برگ، ساقه یا قسمت آسیب‌دیده گیاه بفرست.\n\n"
                "بعد از دریافت عکس، ازت اسم یا نوع گیاه رو می‌پرسم و سپس "
                "تحلیل هوش مصنوعی رو انجام می‌دم."
            ),
        },
    )


async def handle_identify(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)

    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    await set_state(int(bale_id), "identification_waiting_photo")

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                "🔍 <b>شناسایی گیاه</b>\n\n"
                "📷 یک عکس واضح از کل گیاه یا برگ‌هاش بفرست "
                "تا گونه گیاه رو شناسایی کنم و راهنمای نگهداریش رو بفرستم."
            ),
        },
    )



def _normalize_bale_phone(phone: str) -> str:
    phone = phone.strip()
    phone = (
        phone
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if phone.startswith("00"):
        phone = "+" + phone[2:]

    return phone


def _is_valid_bale_phone(phone: str) -> bool:
    normalized = _normalize_bale_phone(phone)
    digits = normalized[1:] if normalized.startswith("+") else normalized
    return digits.isdigit() and 8 <= len(digits) <= 15


async def handle_visit(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    await _register_user(message)

    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        return

    await clear_state(int(bale_id))
    await set_state(int(bale_id), "expert_visit_waiting_name")

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                "📞 <b>درخواست ویزیت متخصص</b>\n\n"
                "لطفاً نام و نام خانوادگی خودت رو وارد کن:"
            ),
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🏠 لغو و بازگشت به منوی اصلی",
                            "callback_data": "home",
                        }
                    ]
                ]
            },
        },
    )


async def _finish_bale_expert_visit(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
    *,
    source: str,
    record_id: int | None,
    name: str,
    phone: str,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        return

    phone = _normalize_bale_phone(phone)

    name_parts = name.strip().split(maxsplit=1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else None

    async with session_scope() as session:
        user_repo = UserRepository(session)

        user = await user_repo.get_by_bale_id(int(bale_id))

        if user is None:
            user, _ = await user_repo.get_or_create_bale(
                int(bale_id),
                username=sender.get("username"),
                first_name=sender.get("first_name"),
                last_name=sender.get("last_name"),
                language_code=sender.get("language_code"),
            )

        await user_repo.update_contact(
            user,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
        )

        visit_record_id: int | None = None

        if source == "direct":
            diagnosis_repo = DiagnosisRepository(session)

            diagnosis = await diagnosis_repo.create(
                user_id=user.id,
                plant_id=None,
                telegram_file_id="bale_direct_expert_visit",
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
                expert_visit_source="bale",
            )

            visit_record_id = diagnosis.id

        elif source == "diagnosis":
            if record_id is None:
                raise ValueError("Diagnosis visit record id is missing")

            diagnosis_repo = DiagnosisRepository(session)
            diagnosis = await diagnosis_repo.get_by_id(record_id)

            if diagnosis is None or diagnosis.user_id != user.id:
                await clear_state(int(bale_id))
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ این درخواست ویزیت دیگر معتبر نیست. لطفاً دوباره اقدام کن.",
                )
                return

            await diagnosis_repo.update(
                diagnosis,
                expert_visit_requested=True,
                expert_visit_source=diagnosis.expert_visit_source or "bale",
            )

            visit_record_id = diagnosis.id

        elif source == "identification":
            if record_id is None:
                raise ValueError("Identification visit record id is missing")

            identification_repo = PlantIdentificationRepository(session)
            identification = await identification_repo.get_by_id(record_id)

            if identification is None or identification.user_id != user.id:
                await clear_state(int(bale_id))
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ این درخواست ویزیت دیگر معتبر نیست. لطفاً دوباره اقدام کن.",
                )
                return

            await identification_repo.update(
                identification,
                expert_visit_requested=True,
                expert_visit_source=identification.expert_visit_source or "bale",
            )

            visit_record_id = identification.id

        else:
            raise ValueError(f"Unknown Bale expert visit source: {source}")

        # PWA admin badge/push مثل فلو Telegram
        await session.flush()
        badge_count = await get_admin_badge_count(session)

        await send_push(
            session,
            title="🌿 گرین ویتا",
            body="درخواست ویزیت متخصص جدید ثبت شد.",
            url="/visits",
            badge_count=badge_count,
        )

    await clear_state(int(bale_id))

    visit_code = (
        f"{20000 + visit_record_id:06d}"
        if visit_record_id is not None
        else "------"
    )

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": (
                "✅ <b>درخواست ویزیت متخصص ثبت شد.</b>\n\n"
                f"🎫 کد درخواست: <b>{visit_code}</b>\n\n"
                "کارشناسان کلینیک گیاه‌پزشکی گرین ویتا "
                "جهت هماهنگی با شما تماس خواهند گرفت. 🌿"
            ),
            "reply_markup": _bale_remove_phone_keyboard_markup(),
        },
    )


async def _run_bale_identification(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    data = await get_data(int(bale_id))
    file_id = data.get("identification_file_id")

    if not file_id:
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ عکس این درخواست پیدا نشد.\n"
                "لطفاً دوباره از «🔍 شناسایی گیاه» شروع کن."
            ),
        )
        return

    await client.send_message(
        chat_id=chat_id,
        text="🔎 در حال شناسایی گیاه با هوش مصنوعی... چند لحظه صبر کن.",
    )

    try:
        image_bytes = await client.download_file(str(file_id))
        ai_provider = get_ai_provider()
        result = await identify_plant_image(
            ai_provider,
            image_bytes,
        )

    except AIProviderError:
        logger.exception(
            "bale_identification_ai_failed",
            bale_user_id=bale_id,
        )
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text=(
                "😔 در حال حاضر امکان شناسایی گیاه وجود نداره.\n"
                "چند دقیقه دیگه دوباره امتحان کن."
            ),
        )
        return

    except Exception:
        logger.exception(
            "bale_identification_unexpected_failure",
            bale_user_id=bale_id,
        )
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text="😔 مشکلی در پردازش عکس پیش اومد. لطفاً دوباره امتحان کن.",
        )
        return

    async with session_scope() as session:
        user_repo = UserRepository(session)
        identification_repo = PlantIdentificationRepository(session)

        user, _ = await user_repo.get_or_create_bale(
            int(bale_id),
            username=sender.get("username"),
            first_name=sender.get("first_name"),
            last_name=sender.get("last_name"),
            language_code=sender.get("language_code"),
        )

        identification = await identification_repo.create(
            user_id=user.id,
            telegram_file_id=str(file_id),
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

    await clear_state(int(bale_id))

    difficulty = {
        DifficultyLevel.EASY: "🟢 آسان",
        DifficultyLevel.MEDIUM: "🟡 متوسط",
        DifficultyLevel.HARD: "🔴 سخت",
        DifficultyLevel.UNKNOWN: "⚪️ نامشخص",
    }.get(result.difficulty_level, "⚪️ نامشخص")

    if not result.parse_succeeded or not result.is_plant:
        text = (
            "⚠️ نتونستم گیاه رو به‌درستی شناسایی کنم.\n\n"
            f"{result.preventive_care_tips or result.raw_response}\n\n"
            "لطفاً با یک عکس واضح‌تر دوباره امتحان کن."
        )
    else:
        lines = [
            f"🌿 {result.persian_name}",
        ]

        if result.scientific_name:
            lines.append(
                f"🔬 نام علمی: {result.scientific_name}"
            )

        lines.append(
            f"📊 اطمینان شناسایی: {result.confidence}٪"
        )
        lines.append(
            f"⚙️ سطح سختی نگهداری: {difficulty}"
        )

        rows = [
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

        for label, value in rows:
            if value:
                lines.append(f"\n{label}: {value}")

        if result.propagation_methods:
            lines.append("\n🌾 روش‌های تکثیر:")
            lines.extend(
                f"• {item}"
                for item in result.propagation_methods
            )

        if result.common_pests:
            lines.append("\n🐛 آفت‌های رایج:")
            lines.extend(
                f"• {item}"
                for item in result.common_pests
            )

        if result.common_diseases:
            lines.append("\n🩺 بیماری‌های رایج:")
            lines.extend(
                f"• {item}"
                for item in result.common_diseases
            )

        if result.preventive_care_tips:
            lines.append(
                f"\n🛡 نکات پیشگیرانه:\n"
                f"{result.preventive_care_tips}"
            )

        lines.append(
            "\n⚠️ این راهنما توسط هوش مصنوعی تولید شده و "
            "برای مراقبت تخصصی‌تر می‌توانی درخواست ویزیت متخصص بدهی."
        )

        text = "\n".join(lines)

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🩺 تشخیص بیماری",
                            "callback_data": "diagnose",
                        }
                    ],
                    [
                        {
                            "text": "📞 درخواست ویزیت متخصص",
                            "callback_data": f"identification_visit:{identification.id}",
                        }
                    ],
                    [
                        {
                            "text": "🏠 منوی اصلی",
                            "callback_data": "home",
                        }
                    ],
                ]
            },
        },
    )


async def _run_bale_diagnosis(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is None:
        raise ValueError("Bale message has no sender id")

    data = await get_data(int(bale_id))

    file_id = data.get("diagnosis_file_id")
    plant_name = data.get("plant_name")
    user_notes = data.get("user_notes")

    if not file_id:
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ عکس این درخواست پیدا نشد.\n"
                "لطفاً دوباره از «🩺 تشخیص بیماری» شروع کن."
            ),
        )
        return

    await client.send_message(
        chat_id=chat_id,
        text="🔎 در حال تحلیل عکس توسط هوش مصنوعی... چند لحظه صبر کن.",
    )

    try:
        image_bytes = await client.download_file(str(file_id))

        ai_provider = get_ai_provider()

        result = await diagnose_plant_image(
            ai_provider,
            image_bytes,
            plant_name=plant_name,
            user_notes=user_notes,
        )

    except AIProviderError:
        logger.exception(
            "bale_diagnosis_ai_failed",
            bale_user_id=bale_id,
        )
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text=(
                "😔 در حال حاضر امکان تحلیل عکس وجود نداره.\n"
                "چند دقیقه دیگه دوباره امتحان کن."
            ),
        )
        return

    except Exception:
        logger.exception(
            "bale_diagnosis_unexpected_failure",
            bale_user_id=bale_id,
        )
        await clear_state(int(bale_id))
        await client.send_message(
            chat_id=chat_id,
            text="😔 مشکلی در پردازش عکس پیش اومد. لطفاً دوباره امتحان کن.",
        )
        return

    async with session_scope() as session:
        user_repo = UserRepository(session)
        diagnosis_repo = DiagnosisRepository(session)

        user, _ = await user_repo.get_or_create_bale(
            int(bale_id),
            username=sender.get("username"),
            first_name=sender.get("first_name"),
            last_name=sender.get("last_name"),
            language_code=sender.get("language_code"),
        )

        diagnosis = await diagnosis_repo.create(
            user_id=user.id,
            plant_id=None,
            telegram_file_id=str(file_id),
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

    severity_emoji = {
        DiagnosisSeverity.NONE: "🟢",
        DiagnosisSeverity.MILD: "🟡",
        DiagnosisSeverity.MODERATE: "🟠",
        DiagnosisSeverity.SEVERE: "🔴",
        DiagnosisSeverity.UNKNOWN: "⚪️",
    }

    lines: list[str] = []

    if plant_name:
        lines.append(f"🌱 گیاه: {plant_name}")

    if result.is_healthy:
        lines.append("✅ گیاه شما سالم به نظر می‌رسد!")
        lines.append(f"📊 میزان اطمینان: {result.confidence}٪")

        if result.symptoms:
            lines.append("\n🔍 موارد بررسی‌شده:")
            lines.extend(f"• {item}" for item in result.symptoms)

        if result.prevention:
            lines.append(
                f"\n🛡 نکات نگهداری:\n{result.prevention}"
            )

    else:
        emoji = severity_emoji.get(result.severity, "⚪️")

        lines.append(
            f"1️⃣ تشخیص: {emoji} {result.disease_name}"
        )
        lines.append(
            f"📊 میزان اطمینان تشخیص: {result.confidence}٪"
        )

        if result.symptoms:
            lines.append("\n🔍 علائم مشاهده‌شده:")
            lines.extend(
                f"• {item}"
                for item in result.symptoms
            )

        lines.append(
            "\n2️⃣ علت:\n"
            f"{result.cause or 'علت مشخصی گزارش نشده است.'}"
        )

        lines.append(
            "\n3️⃣ درمان:\n"
            f"{result.treatment or 'توصیه درمانی مشخصی گزارش نشده است.'}"
        )

        if result.prevention:
            lines.append(
                f"\n🛡 پیشگیری از تکرار:\n{result.prevention}"
            )

    lines.append(
        "\n⚠️ این تحلیل توسط هوش مصنوعی انجام شده و "
        "جایگزین ویزیت تخصصی نیست."
    )

    await clear_state(int(bale_id))

    await client.call(
        "sendMessage",
        json={
            "chat_id": chat_id,
            "text": "\n".join(lines),
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 درخواست ویزیت متخصص",
                            "callback_data": f"diagnosis_visit:{diagnosis.id}",
                        }
                    ],
                    [
                        {
                            "text": "🏠 منوی اصلی",
                            "callback_data": "home",
                        }
                    ],
                ]
            },
        },
    )


async def dispatch_message(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if bale_id is not None:
        current_state = await get_state(int(bale_id))

        # Contact ارسالی از دکمه request_contact در بله
        contact = message.get("contact") or {}
        contact_phone = (contact.get("phone_number") or "").strip()

        # عکس در مرحله تشخیص
        if message.get("photo") and current_state == "diagnosis_waiting_photo":
            photos = message.get("photo") or []

            if not photos:
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ عکس دریافت نشد. لطفاً دوباره عکس را ارسال کن.",
                )
                return

            largest_photo = photos[-1]
            bale_file_id = largest_photo.get("file_id")

            if not bale_file_id:
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ شناسه عکس دریافت نشد. لطفاً دوباره عکس را ارسال کن.",
                )
                return

            await update_data(
                int(bale_id),
                diagnosis_file_id=str(bale_file_id),
            )

            await set_state(
                int(bale_id),
                "diagnosis_waiting_plant_name",
            )

            logger.info(
                "Bale diagnosis photo stored: bale_id=%s file_id=%s",
                bale_id,
                bale_file_id,
            )

            await client.send_message(
                chat_id=chat_id,
                text=(
                    "✅ عکس رو دریافت کردم.\n\n"
                    "🌱 اسم یا نوع این گیاه رو می‌دونی؟\n"
                    "مثلاً: مونسترا، پتوس، ارکیده...\n"
                    "اگه نمی‌دونی، بنویس «نمی‌دونم»."
                ),
            )
            return

        # عکس در مرحله شناسایی
        if message.get("photo") and current_state == "identification_waiting_photo":
            photos = message.get("photo") or []

            if not photos:
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ عکس دریافت نشد. لطفاً دوباره عکس را ارسال کن.",
                )
                return

            largest_photo = photos[-1]
            bale_file_id = largest_photo.get("file_id")

            if not bale_file_id:
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ شناسه عکس دریافت نشد. لطفاً دوباره عکس را ارسال کن.",
                )
                return

            await update_data(
                int(bale_id),
                identification_file_id=str(bale_file_id),
            )

            await set_state(
                int(bale_id),
                "identification_processing",
            )

            logger.info(
                "Bale identification photo stored: bale_id=%s file_id=%s",
                bale_id,
                bale_file_id,
            )

            await _run_bale_identification(
                client,
                message,
                chat_id,
            )
            return

    text = (message.get("text") or "").strip()
    command = _command_name(text) if text.startswith("/") else ""

    # ---------------------------------------------------------
    # Bale phone/contact state
    # ---------------------------------------------------------
    # Contact پیام متنی ندارد، بنابراین باید قبل از شرط
    # "text and not command" پردازش شود.
    if bale_id is not None and current_state == "expert_visit_waiting_phone":
        phone = contact_phone or text.strip()

        if not phone:
            return

        if not _is_valid_bale_phone(phone):
            await client.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ شماره تلفن معتبر نیست.\n\n"
                    "مثلاً:\n"
                    "09121234567"
                ),
            )
            return

        data = await get_data(int(bale_id))

        name = data.get("expert_visit_name")
        source = data.get("expert_visit_source", "direct")
        record_id = data.get("expert_visit_id")

        if not name:
            await clear_state(int(bale_id))
            await client.send_message(
                chat_id=chat_id,
                text="⚠️ اطلاعات درخواست ناقص شده. لطفاً دوباره درخواست ویزیت بده.",
                reply_markup={
                    "remove_keyboard": True
                },
            )
            return

        await _finish_bale_expert_visit(
            client,
            message,
            chat_id,
            source=str(source),
            record_id=int(record_id) if record_id is not None else None,
            name=str(name),
            phone=phone,
        )

        return

    # ---------------------------------------------------------
    # Bale diagnosis conversation states
    # ---------------------------------------------------------
    if bale_id is not None and text and not command:
        current_state = await get_state(int(bale_id))

        if current_state == "plant_waiting_name":
            name = text.strip()

            if not name:
                await client.send_message(
                    chat_id=chat_id,
                    text="🌱 لطفاً نام گیاه را وارد کن.",
                )
                return

            await update_data(
                int(bale_id),
                plant_name=name,
            )

            await set_state(
                int(bale_id),
                "plant_waiting_species",
            )

            await client.call(
                "sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "🔍 نوع یا گونه گیاه رو می‌دونی؟\n\n"
                        "مثلاً: مونسترا، پتوس، ارکیده\n\n"
                        "اگر نمی‌دونی، «ندارم» بنویس."
                    ),
                },
            )
            return

        if current_state == "plant_waiting_species":
            data = await get_data(int(bale_id))

            name = data.get("plant_name")

            if not name:
                await clear_state(int(bale_id))
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ این درخواست منقضی شده. دوباره از «🌱 گیاهان من» شروع کن.",
                )
                return

            species = None if text in {
                "ندارم",
                "-",
                "نمی‌دونم",
                "نمیدونم",
                "نمی دانم",
            } else text

            async with session_scope() as session:
                user_repo = UserRepository(session)
                plant_repo = PlantRepository(session)

                user, _ = await user_repo.get_or_create_bale(
                    int(bale_id),
                )

                plant = await plant_repo.create(
                    owner_id=user.id,
                    name=name,
                    species=species,
                )

            await clear_state(int(bale_id))

            await client.call(
                "sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        f"✅ پرونده «{plant.name}» با موفقیت ساخته شد.\n\n"
                        f"🌱 نام: {plant.name}\n"
                        f"🔍 نوع/گونه: {plant.species or 'نامشخص'}\n"
                        "📊 وضعیت سلامت: ⚪️ نامشخص"
                    ),
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🌱 گیاهان من",
                                    "callback_data": "plants",
                                }
                            ],
                            [
                                {
                                    "text": "🏠 منوی اصلی",
                                    "callback_data": "home",
                                }
                            ],
                        ]
                    },
                },
            )
            return

        if current_state == "expert_visit_waiting_name":
            name = text.strip()

            if len(name) < 2:
                await client.send_message(
                    chat_id=chat_id,
                    text="⚠️ لطفاً نام و نام خانوادگی معتبر وارد کن.",
                )
                return

            await update_data(
                int(bale_id),
                expert_visit_name=name,
            )

            await set_state(
                int(bale_id),
                "expert_visit_waiting_phone",
            )

            await client.send_message(
                chat_id=chat_id,
                text=(
                    "📱 شماره تلفنت رو ارسال کن.\n\n"
                    "می‌تونی از دکمهٔ زیر برای ارسال مستقیم شماره استفاده کنی.\n"
                    "یا شماره رو دستی وارد کنی؛ مثلاً:\n"
                    "09121234567"
                ),
                reply_markup=_bale_phone_request_markup(),
            )
            return

        if current_state == "diagnosis_waiting_plant_name":
            plant_name = None if text in {
                "نمی‌دونم",
                "نمیدونم",
                "نمی دانم",
                "-",
                "ندارم",
            } else text

            await update_data(
                int(bale_id),
                plant_name=plant_name,
            )

            await set_state(
                int(bale_id),
                "diagnosis_waiting_details",
            )

            await client.send_message(
                chat_id=chat_id,
                text=(
                    "📝 توضیح بیشتری درباره وضعیت گیاه داری؟\n\n"
                    "مثلاً از کی این علائم رو دیدی، کجا نگهداریش می‌کنی، "
                    "چند وقت یک‌بار آبش می‌دی و چه تغییراتی اخیراً داشته.\n\n"
                    "اگر توضیحی نداری، بنویس «ندارم»."
                ),
            )
            return

        if current_state == "diagnosis_waiting_details":
            user_notes = None if text in {
                "ندارم",
                "-",
                "ندونم",
                "نمی‌دونم",
                "نمیدونم",
            } else text

            await update_data(
                int(bale_id),
                user_notes=user_notes,
            )

            await _run_bale_diagnosis(
                client,
                message,
                chat_id,
            )
            return

    if command == "/start" or text == "🏠 شروع":
        await handle_start(client, message, chat_id)

    elif command == "/help":
        await handle_help(client, message, chat_id)

    elif command == "/about":
        await handle_about(client, message, chat_id)

    elif command == "/plants":
        await handle_plants(client, message, chat_id)

    elif command == "/diagnose":
        await handle_diagnose(client, message, chat_id)

    elif command == "/identify":
        await handle_identify(client, message, chat_id)

    else:
        sender = message.get("from") or {}

        if sender.get("id") is not None:
            await _register_user(message)

        if text:
            await _send_menu(
                client,
                chat_id=chat_id,
                text=UNKNOWN_TEXT,
            )


async def dispatch_callback(
    client: Any,
    message: dict[str, Any],
    chat_id: int,
    data: str,
) -> None:
    sender = message.get("from") or {}
    bale_id = sender.get("id")

    if data == "home":
        if bale_id is not None:
            await clear_state(int(bale_id))

        await handle_start(client, message, chat_id)
        return

    if data == "plants":
        if bale_id is not None:
            await clear_state(int(bale_id))

        await handle_plants(client, message, chat_id)
        return

    if data == "plant_add":
        if bale_id is None:
            return

        await clear_state(int(bale_id))
        await set_state(
            int(bale_id),
            "plant_waiting_name",
        )

        await client.call(
            "sendMessage",
            json={
                "chat_id": chat_id,
                "text": (
                    "➕ <b>افزودن گیاه جدید</b>\n\n"
                    "🌱 اسم این گیاه رو چی می‌ذاری؟\n"
                    "مثلاً: مونسترای اتاق پذیرایی"
                ),
            },
        )
        return

    if data.startswith("plant_view:"):
        try:
            plant_id = int(data.split(":", 1)[1])
        except ValueError:
            await client.send_message(
                chat_id=chat_id,
                text="⚠️ شناسه گیاه نامعتبر است.",
            )
            return

        await _handle_bale_plant_view(
            client,
            message,
            chat_id,
            plant_id,
        )
        return

    if data.startswith("plant_delete:"):
        try:
            plant_id = int(data.split(":", 1)[1])
        except ValueError:
            return

        await _handle_bale_plant_delete_request(
            client,
            message,
            chat_id,
            plant_id,
        )
        return

    if data.startswith("plant_delete_confirm:"):
        try:
            plant_id = int(data.split(":", 1)[1])
        except ValueError:
            return

        await _handle_bale_plant_delete_confirm(
            client,
            message,
            chat_id,
            plant_id,
        )
        return

    elif data.startswith("diagnosis_visit:"):
        if bale_id is None:
            return

        try:
            record_id = int(data.split(":", 1)[1])
        except ValueError:
            await client.send_message(
                chat_id=chat_id,
                text="⚠️ شناسه درخواست نامعتبر است.",
            )
            return

        await clear_state(int(bale_id))

        await update_data(
            int(bale_id),
            expert_visit_source="diagnosis",
            expert_visit_id=record_id,
            expert_visit_name=None,
        )

        await set_state(
            int(bale_id),
            "expert_visit_waiting_name",
        )

        await client.send_message(
            chat_id=chat_id,
            text=(
                "📞 <b>درخواست ویزیت متخصص</b>\n\n"
                "برای ثبت درخواست، لطفاً نام و نام خانوادگی خودت رو وارد کن:"
            ),
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "🏠 لغو و بازگشت به منوی اصلی",
                            "callback_data": "home",
                        }
                    ]
                ]
            },
        )
        return

    elif data.startswith("identification_visit:"):
        if bale_id is None:
            return

        try:
            record_id = int(data.split(":", 1)[1])
        except ValueError:
            await client.send_message(
                chat_id=chat_id,
                text="⚠️ شناسه درخواست نامعتبر است.",
            )
            return

        await clear_state(int(bale_id))

        await update_data(
            int(bale_id),
            expert_visit_source="identification",
            expert_visit_id=record_id,
            expert_visit_name=None,
        )

        await set_state(
            int(bale_id),
            "expert_visit_waiting_name",
        )

        await client.send_message(
            chat_id=chat_id,
            text=(
                "📞 <b>درخواست ویزیت متخصص</b>\n\n"
                "برای ثبت درخواست، لطفاً نام و نام خانوادگی خودت رو وارد کن:"
            ),
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "🏠 لغو و بازگشت به منوی اصلی",
                            "callback_data": "home",
                        }
                    ]
                ]
            },
        )
        return

    elif data == "diagnose":
        await handle_diagnose(client, message, chat_id)

    elif data == "identify":
        await handle_identify(client, message, chat_id)

    elif data == "plants":
        await handle_plants(client, message, chat_id)

    elif data == "visit":
        await handle_visit(client, message, chat_id)

    elif data == "about":
        await handle_about(client, message, chat_id)

    elif data == "help":
        await handle_help(client, message, chat_id)

    else:
        await _send_menu(
            client,
            chat_id=chat_id,
            text="🌿 گزینه ناشناخته است.",
        )

