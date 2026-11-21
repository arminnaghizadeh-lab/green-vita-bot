from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pwdlib import PasswordHash
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError

from src.admin.auth import require_authentication
from src.db.models.user import User
from src.db.models.booking import Booking, BookingTimeSlot, Service
from src.db.models.web_account import WebAccount, WebDiagnosisUsage, WebPasswordResetToken
from src.invoices.models import InvCustomer, Invoice
from src.db.session import AsyncSessionLocal

router = APIRouter(prefix="/account", tags=["web-account"])
templates = Jinja2Templates(directory="src/admin/templates")
password_hasher = PasswordHash.recommended()
SESSION_KEY = "web_account_id"


def normalize_phone(value: str) -> str:
    # Convert Persian/Arabic numerals only. Do not strip or rewrite prefixes.
    return value.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    ))


def valid_persian_name(value: str) -> bool:
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    letters_only = re.sub(r"[\s‌]", "", name)
    return (
        len(letters_only) >= 3
        and re.fullmatch(r"[آ-یءٔ‌ ]+", name) is not None
    )


def password_meets_policy(password: str) -> bool:
    return (
        len(password) >= 8
        and any(ch.isalpha() for ch in password)
        and any(ch.isdigit() for ch in password)
    )


def account_id_from_session(request: Request) -> int | None:
    try:
        value = request.session.get(SESSION_KEY)
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def auth_page(
    request: Request,
    page: str,
    *,
    error: str | None = None,
    message: str | None = None,
    status_code: int = 200,
    values: dict | None = None,
):
    context = {
        "request": request,
        "error": error,
        "message": message,
    }
    if values:
        context.update(values)
    return templates.TemplateResponse(
        f"public/account_{page}.html", context, status_code=status_code
    )


@router.get("/api/me", include_in_schema=False)
async def account_me(request: Request):
    account_id = account_id_from_session(request)
    if account_id is None:
        return JSONResponse({"authenticated": False}, status_code=401)

    async with AsyncSessionLocal() as session:
        account = await session.get(WebAccount, account_id)
        if account is None or not account.is_active:
            request.session.pop(SESSION_KEY, None)
            return JSONResponse({"authenticated": False}, status_code=401)

        user = await session.get(User, account.user_id)
        if user is None:
            request.session.pop(SESSION_KEY, None)
            return JSONResponse({"authenticated": False}, status_code=401)

        return JSONResponse({
            "authenticated": True,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "phone_number": account.phone_number or "",
        })


@router.get("/", include_in_schema=False)
async def account_root(request: Request):
    destination = (
        "/account/profile/" if account_id_from_session(request)
        else "/account/login/"
    )
    return RedirectResponse(destination, status_code=303)


@router.get("/register/", include_in_schema=False)
async def register_page(request: Request):
    if account_id_from_session(request):
        return RedirectResponse("/account/profile/", status_code=303)
    return auth_page(request, "register")


@router.post("/register/", include_in_schema=False)
async def register(
    request: Request,
    first_name: str = Form(..., max_length=80),
    last_name: str = Form(..., max_length=80),
    phone_number: str = Form(..., max_length=40),
    password: str = Form(..., min_length=8, max_length=128),
    password_confirm: str = Form(..., min_length=8, max_length=128),
):
    first_name = re.sub(r"\s+", " ", first_name).strip()
    last_name = re.sub(r"\s+", " ", last_name).strip()
    phone = normalize_phone(phone_number)

    values = {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone,
    }

    if not valid_persian_name(first_name) or not valid_persian_name(last_name):
        return auth_page(
            request, "register",
            error="نام و نام خانوادگی باید حداقل ۳ حرف فارسی باشد.",
            status_code=400, values=values,
        )

    if not re.fullmatch(r"09\d{9}", phone):
        return auth_page(
            request, "register",
            error="شماره باید دقیقاً ۱۱ رقم و با 09 شروع شود؛ مثل 09123456789.",
            status_code=400, values=values,
        )

    if password != password_confirm:
        return auth_page(
            request, "register", error="تکرار رمز با رمز عبور یکسان نیست.",
            status_code=400, values=values,
        )

    if not password_meets_policy(password):
        return auth_page(
            request, "register",
            error="رمز عبور باید حداقل ۸ کاراکتر و شامل دست‌کم یک حرف و یک عدد باشد.",
            status_code=400, values=values,
        )

    async with AsyncSessionLocal() as session:
        exists = await session.scalar(
            select(WebAccount.id).where(WebAccount.phone_number == phone)
        )
        if exists is not None:
            return auth_page(
                request, "register",
                error="برای این شماره قبلاً حساب ساخته شده است؛ وارد شو.",
                status_code=409, values=values,
            )

        user = User(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
        )
        session.add(user)
        await session.flush()

        account = WebAccount(
            user_id=user.id,
            phone_number=phone,
            password_hash=password_hasher.hash(password),
        )
        session.add(account)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return auth_page(
                request, "register",
                error="این شماره هم‌اکنون ثبت شده است؛ لطفاً وارد شو.",
                status_code=409, values=values,
            )

        new_account_id = account.id

    # Keep the existing admin session intact; only set the web-account key.
    request.session[SESSION_KEY] = new_account_id
    return RedirectResponse("/account/profile/", status_code=303)


@router.get("/login/", include_in_schema=False)
async def login_page(request: Request):
    if account_id_from_session(request):
        return RedirectResponse("/account/profile/", status_code=303)

    message = (
        "رمز عبور با موفقیت تغییر کرد؛ اکنون وارد حساب شو."
        if request.query_params.get("reset") == "success"
        else None
    )
    return auth_page(request, "login", message=message)


@router.post("/login/", include_in_schema=False)
async def login(
    request: Request,
    phone_number: str = Form(..., max_length=40),
    password: str = Form(..., max_length=128),
):
    phone = normalize_phone(phone_number)

    if not re.fullmatch(r"09[0-9]{9}", phone):
        return auth_page(
            request, "login",
            error="شماره تلفن یا رمز عبور درست نیست.",
            status_code=401,
            values={"phone_number": phone},
        )

    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(WebAccount).where(
                WebAccount.phone_number == phone,
                WebAccount.is_active.is_(True),
            )
        )

        if account is None or not password_hasher.verify(
            password, account.password_hash
        ):
            return auth_page(
                request, "login",
                error="شماره تلفن یا رمز عبور درست نیست.",
                status_code=401,
                values={"phone_number": phone},
            )

        account.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        authenticated_id = account.id

    request.session[SESSION_KEY] = authenticated_id
    return RedirectResponse("/account/profile/", status_code=303)


@router.post("/logout/", include_in_schema=False)
async def logout(request: Request):
    request.session.pop(SESSION_KEY, None)
    return RedirectResponse("/account/login/", status_code=303)


@router.get("/profile/", include_in_schema=False)
async def profile(request: Request):
    account_id = account_id_from_session(request)
    if account_id is None:
        return RedirectResponse("/account/login/", status_code=303)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WebAccount, User)
            .join(User, User.id == WebAccount.user_id)
            .where(
                WebAccount.id == account_id,
                WebAccount.is_active.is_(True),
            )
        )
        pair = result.one_or_none()
        if pair is None:
            request.session.pop(SESSION_KEY, None)
            return RedirectResponse("/account/login/", status_code=303)

        account, user = pair

        booking_rows = await session.execute(
            select(Booking, Service, BookingTimeSlot)
            .join(Service, Service.id == Booking.service_id)
            .join(BookingTimeSlot, BookingTimeSlot.id == Booking.time_slot_id)
            .where(Booking.user_id == user.id)
            .order_by(Booking.created_at.desc())
            .limit(50)
        )
        bookings = [
            {"booking": booking, "service": service, "slot": slot}
            for booking, service, slot in booking_rows.all()
        ]

        usage_rows = await session.scalars(
            select(WebDiagnosisUsage)
            .where(WebDiagnosisUsage.account_id == account.id)
            .order_by(WebDiagnosisUsage.created_at.desc())
            .limit(50)
        )
        diagnoses = list(usage_rows.all())

        invoice_customer = await session.scalar(
            select(InvCustomer).where(
                InvCustomer.web_account_id == account.id
            )
        )

        invoices = []

        if invoice_customer is not None:
            invoice_rows = await session.scalars(
                select(Invoice)
                .where(
                    Invoice.customer_id == invoice_customer.id,
                    Invoice.status.in_(("final", "void")),
                )
                .order_by(Invoice.created_at.desc())
                .limit(50)
            )

            for invoice in invoice_rows:
                payload = (
                    invoice.data
                    if isinstance(invoice.data, dict)
                    else {}
                )

                invoices.append({
                    "no": invoice.no,
                    "date": invoice.date_text or str(payload.get("date", "")),
                    "status": invoice.status,
                    "payable_text": f"{invoice.payable:,}".replace(",", "٬"),
                })

    return templates.TemplateResponse(
        "public/account_profile.html",
        {
            "request": request,
            "account": account,
            "user": user,
            "bookings": bookings,
            "diagnoses": diagnoses,
            "invoice_customer": invoice_customer,
            "invoices": invoices,
            "tehran": ZoneInfo("Asia/Tehran"),
        },
    )




CUSTOMER_LINK_CSRF_SESSION_KEY = "admin_customer_links_csrf"


def _customer_links_csrf_token(request: Request) -> str:
    token = request.session.get(CUSTOMER_LINK_CSRF_SESSION_KEY)
    if not isinstance(token, str) or len(token) < 32 or not token.isascii():
        token = secrets.token_urlsafe(32)
        request.session[CUSTOMER_LINK_CSRF_SESSION_KEY] = token
    return token


async def _customer_links_response(
    request: Request,
    *,
    error: str | None = None,
    status_code: int = 200,
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WebAccount, User, InvCustomer)
            .join(User, User.id == WebAccount.user_id)
            .outerjoin(
                InvCustomer,
                InvCustomer.web_account_id == WebAccount.id,
            )
            .where(WebAccount.is_active.is_(True))
            .order_by(WebAccount.id.desc())
        )

        rows = [
            {"account": account, "user": user, "customer": customer}
            for account, user, customer in result.all()
        ]

        customers = (
            await session.scalars(
                select(InvCustomer).order_by(
                    InvCustomer.name,
                    InvCustomer.id,
                )
            )
        ).all()

    return templates.TemplateResponse(
        "account_customer_links.html",
        {
            "request": request,
            "rows": rows,
            "customers": customers,
            "csrf_token": _customer_links_csrf_token(request),
            "error": error,
            "updated": request.query_params.get("updated") == "1",
        },
        status_code=status_code,
    )


@router.get("/admin/customer-links/", include_in_schema=False)
async def admin_customer_links_page(request: Request):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    return await _customer_links_response(request)


@router.post("/admin/customer-links/", include_in_schema=False)
async def admin_save_customer_link(
    request: Request,
    account_id: int = Form(...),
    customer_id: str = Form(default=""),
    csrf_token: str = Form(...),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    expected_csrf = request.session.get(CUSTOMER_LINK_CSRF_SESSION_KEY)
    valid_csrf = (
        isinstance(expected_csrf, str)
        and isinstance(csrf_token, str)
        and expected_csrf.isascii()
        and csrf_token.isascii()
        and secrets.compare_digest(expected_csrf, csrf_token)
    )
    if not valid_csrf:
        return await _customer_links_response(
            request,
            error="درخواست معتبر نیست یا نشست شما منقضی شده است. صفحه را تازه‌سازی کنید.",
            status_code=403,
        )

    target_id = None
    if customer_id.strip():
        try:
            target_id = int(customer_id.strip())
            if target_id <= 0:
                raise ValueError
        except ValueError:
            return await _customer_links_response(
                request,
                error="شناسه مشتری معتبر نیست.",
                status_code=400,
            )

    error = None

    try:
        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(WebAccount)
                .where(
                    WebAccount.id == account_id,
                    WebAccount.is_active.is_(True),
                )
                .with_for_update()
            )

            if account is None:
                error = "حساب فعال موردنظر پیدا نشد."
            else:
                target = None

                if target_id is not None:
                    target = await session.scalar(
                        select(InvCustomer)
                        .where(InvCustomer.id == target_id)
                        .with_for_update()
                    )

                    if target is None:
                        error = "پرونده مشتری پیدا نشد."
                    elif (
                        target.web_account_id is not None
                        and target.web_account_id != account.id
                    ):
                        error = "این مشتری قبلاً به حساب دیگری متصل شده است."

                if error is None:
                    current = await session.scalar(
                        select(InvCustomer)
                        .where(InvCustomer.web_account_id == account.id)
                        .with_for_update()
                    )

                    if current is not None and (
                        target is None or current.id != target.id
                    ):
                        current.web_account_id = None

                    if target is not None:
                        target.web_account_id = account.id

                    try:
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        error = "ثبت اتصال انجام نشد؛ احتمالاً مشتری به حساب دیگری متصل شده است."

    except Exception:
        error = "خطا در ذخیره اتصال مشتری به حساب کاربری."

    if error:
        return await _customer_links_response(
            request,
            error=error,
            status_code=409,
        )

    return RedirectResponse(
        "/account/admin/customer-links/?updated=1",
        status_code=303,
    )


# Password-recovery links are generated only in the authenticated admin panel.
PUBLIC_SITE_URL = "https://greenvitaclinic.ir"
RESET_TOKEN_MINUTES = 30


def _reset_token_is_valid(token_row, now: datetime) -> bool:
    if token_row is None or token_row.used_at is not None:
        return False
    expires = token_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > now


def _reset_page(
    request: Request,
    *,
    token: str | None = None,
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        "public/account_reset.html",
        {
            "request": request,
            "token": token,
            "error": error,
        },
        status_code=status_code,
    )


async def _admin_reset_page(
    request: Request,
    *,
    error: str | None = None,
    message: str | None = None,
    reset_url: str | None = None,
    phone_number: str = "",
    status_code: int = 200,
):
    async with AsyncSessionLocal() as session:
        counts = {
            "customers": await session.scalar(
                select(func.count(InvCustomer.id)).where(
                    InvCustomer.web_account_id.is_(None)
                )
            ),
            "customers_linked": await session.scalar(
                select(func.count(InvCustomer.id)).where(
                    InvCustomer.web_account_id.is_not(None)
                )
            ),
            "site": await session.scalar(
                select(func.count(WebAccount.id))
            ),
            "site_active": await session.scalar(
                select(func.count(WebAccount.id)).where(
                    WebAccount.is_active.is_(True)
                )
            ),
            "site_inactive": await session.scalar(
                select(func.count(WebAccount.id)).where(
                    WebAccount.is_active.is_(False)
                )
            ),
            "bots": await session.scalar(
                select(func.count(User.id)).where(
                    or_(
                        User.telegram_id.is_not(None),
                        User.bale_id.is_not(None),
                    )
                )
            ),
            "telegram": await session.scalar(
                select(func.count(User.id)).where(
                    User.telegram_id.is_not(None)
                )
            ),
            "bale": await session.scalar(
                select(func.count(User.id)).where(
                    User.bale_id.is_not(None)
                )
            ),
            "both": await session.scalar(
                select(func.count(User.id)).where(
                    User.telegram_id.is_not(None),
                    User.bale_id.is_not(None),
                )
            ),
        }
        counts = {key: int(value or 0) for key, value in counts.items()}

    return templates.TemplateResponse(
        "account_admin_users.html",
        {
            "request": request,
            "tab": "reset",
            "q": "",
            "page": 1,
            "page_size": 40,
            "total_rows": 0,
            "total_pages": 1,
            "counts": counts,
            "customer_rows": [],
            "site_rows": [],
            "bot_rows": [],
            "csrf_token": _customer_links_csrf_token(request),
            "reset_error": error,
            "reset_message": message,
            "reset_url": reset_url,
            "reset_phone_number": phone_number,
            "expires_minutes": RESET_TOKEN_MINUTES,
        },
        status_code=status_code,
    )


@router.get("/admin/password-reset/", include_in_schema=False)
async def admin_password_reset_page(request: Request):
    redirect = require_authentication(request)
    if redirect:
        return redirect
    return RedirectResponse(
        "/account/admin/users/?tab=reset",
        status_code=303,
    )


@router.post("/admin/password-reset/", include_in_schema=False)
async def admin_create_password_reset(
    request: Request,
    phone_number: str = Form(..., max_length=40),
    csrf_token: str = Form(...),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    expected_csrf = request.session.get(CUSTOMER_LINK_CSRF_SESSION_KEY)
    valid_csrf = (
        isinstance(expected_csrf, str)
        and isinstance(csrf_token, str)
        and expected_csrf.isascii()
        and csrf_token.isascii()
        and secrets.compare_digest(expected_csrf, csrf_token)
    )
    if not valid_csrf:
        return await _admin_reset_page(
            request,
            error="درخواست معتبر نیست یا نشست شما منقضی شده است. صفحه را تازه‌سازی کنید.",
            phone_number=phone_number,
            status_code=403,
        )

    phone = normalize_phone(phone_number)
    if not re.fullmatch(r"09\d{9}", phone):
        return await _admin_reset_page(
            request,
            error="شماره باید دقیقاً ۱۱ رقم و با 09 شروع شود؛ مثل 09123456789.",
            phone_number=phone,
            status_code=400,
        )

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(WebAccount)
            .where(
                WebAccount.phone_number == phone,
                WebAccount.is_active.is_(True),
            )
            .with_for_update()
        )

        if account is None:
            return await _admin_reset_page(
                request,
                error="حساب فعال با این شماره پیدا نشد.",
                phone_number=phone,
                status_code=404,
            )

        old_tokens = await session.scalars(
            select(WebPasswordResetToken)
            .where(
                WebPasswordResetToken.account_id == account.id,
                WebPasswordResetToken.used_at.is_(None),
            )
            .with_for_update()
        )
        for old_token in old_tokens:
            old_token.used_at = now

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        session.add(
            WebPasswordResetToken(
                account_id=account.id,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=RESET_TOKEN_MINUTES),
            )
        )
        await session.commit()

    reset_url = f"{PUBLIC_SITE_URL}/account/reset/{raw_token}/"
    return await _admin_reset_page(
        request,
        message="لینک یک‌بارمصرف ساخته شد. پیش از ارسال، هویت دریافت‌کننده را تأیید کن.",
        reset_url=reset_url,
        phone_number=phone,
    )


@router.get("/reset/{token}/", include_in_schema=False)
async def password_reset_page(request: Request, token: str):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        token_row = await session.scalar(
            select(WebPasswordResetToken).where(
                WebPasswordResetToken.token_hash == token_hash
            )
        )
        account = None
        if _reset_token_is_valid(token_row, now):
            account = await session.get(WebAccount, token_row.account_id)

        if account is None or not account.is_active:
            return _reset_page(
                request,
                error="این لینک نامعتبر یا منقضی شده است؛ از مدیر لینک جدید بگیر.",
                status_code=400,
            )

    return _reset_page(request, token=token)


@router.post("/reset/{token}/", include_in_schema=False)
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(..., min_length=8, max_length=128),
    password_confirm: str = Form(..., min_length=8, max_length=128),
):
    if password != password_confirm:
        return _reset_page(
            request,
            token=token,
            error="تکرار رمز عبور با رمز جدید یکسان نیست.",
            status_code=400,
        )

    if not password_meets_policy(password):
        return _reset_page(
            request,
            token=token,
            error="رمز عبور باید حداقل ۸ کاراکتر و شامل دست‌کم یک حرف و یک عدد باشد.",
            status_code=400,
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        token_row = await session.scalar(
            select(WebPasswordResetToken)
            .where(WebPasswordResetToken.token_hash == token_hash)
            .with_for_update()
        )

        if not _reset_token_is_valid(token_row, now):
            return _reset_page(
                request,
                error="این لینک قبلاً استفاده شده یا منقضی شده است؛ از مدیر لینک جدید بگیر.",
                status_code=400,
            )

        account = await session.scalar(
            select(WebAccount)
            .where(
                WebAccount.id == token_row.account_id,
                WebAccount.is_active.is_(True),
            )
            .with_for_update()
        )
        if account is None:
            return _reset_page(
                request,
                error="حساب فعال پیدا نشد؛ با مدیر تماس بگیر.",
                status_code=400,
            )

        account.password_hash = password_hasher.hash(password)

        token_rows = await session.scalars(
            select(WebPasswordResetToken)
            .where(
                WebPasswordResetToken.account_id == account.id,
                WebPasswordResetToken.used_at.is_(None),
            )
            .with_for_update()
        )
        for row in token_rows:
            row.used_at = now

        await session.commit()

    request.session.pop(SESSION_KEY, None)
    return RedirectResponse("/account/login/?reset=success", status_code=303)

# GV ADMIN USERS AND CUSTOMERS DIRECTORY V1
@router.get("/admin/users/", include_in_schema=False)
async def admin_users_directory(
    request: Request,
    tab: str = "customers",
    q: str = "",
    page: int = 1,
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    allowed_tabs = {"customers", "site", "bots", "reset"}
    if tab not in allowed_tabs:
        tab = "customers"

    q = (q or "").strip()[:100]
    page = max(1, page)
    page_size = 40
    offset = (page - 1) * page_size
    pattern = f"%{q}%"

    customer_rows = []
    site_rows = []
    bot_rows = []
    total_rows = 0

    async with AsyncSessionLocal() as session:
        # Summary counts: each group is counted independently.
        counts = {
            "customers": await session.scalar(
                select(func.count(InvCustomer.id)).where(
                    InvCustomer.web_account_id.is_(None)
                )
            ),
            "customers_linked": await session.scalar(
                select(func.count(InvCustomer.id)).where(
                    InvCustomer.web_account_id.is_not(None)
                )
            ),
            "site": await session.scalar(
                select(func.count(WebAccount.id))
            ),
            "site_active": await session.scalar(
                select(func.count(WebAccount.id)).where(
                    WebAccount.is_active.is_(True)
                )
            ),
            "site_inactive": await session.scalar(
                select(func.count(WebAccount.id)).where(
                    WebAccount.is_active.is_(False)
                )
            ),
            "bots": await session.scalar(
                select(func.count(User.id)).where(
                    or_(
                        User.telegram_id.is_not(None),
                        User.bale_id.is_not(None),
                    )
                )
            ),
            "telegram": await session.scalar(
                select(func.count(User.id)).where(
                    User.telegram_id.is_not(None)
                )
            ),
            "bale": await session.scalar(
                select(func.count(User.id)).where(
                    User.bale_id.is_not(None)
                )
            ),
            "both": await session.scalar(
                select(func.count(User.id)).where(
                    User.telegram_id.is_not(None),
                    User.bale_id.is_not(None),
                )
            ),
        }
        counts = {key: int(value or 0) for key, value in counts.items()}

        if tab == "customers":
            filters = [InvCustomer.web_account_id.is_(None)]

            if q:
                filters.append(
                    or_(
                        InvCustomer.name.ilike(pattern),
                        func.coalesce(
                            InvCustomer.data["phone"].astext, ""
                        ).ilike(pattern),
                        cast(InvCustomer.id, String).ilike(pattern),
                    )
                )

            total_rows = int(
                await session.scalar(
                    select(func.count(InvCustomer.id)).where(*filters)
                ) or 0
            )

            invoice_count = (
                select(func.count(Invoice.id))
                .where(Invoice.customer_id == InvCustomer.id)
                .correlate(InvCustomer)
                .scalar_subquery()
            )

            result = await session.execute(
                select(
                    InvCustomer,
                    invoice_count.label("invoice_count"),
                )
                .where(*filters)
                .order_by(InvCustomer.id.desc())
                .offset(offset)
                .limit(page_size)
            )

            customer_rows = [
                {
                    "customer": customer,
                    "invoice_count": int(invoice_total or 0),
                }
                for customer, invoice_total in result.all()
            ]

        elif tab == "site":
            filters = []

            if q:
                filters.append(
                    or_(
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        WebAccount.phone_number.ilike(pattern),
                        cast(WebAccount.id, String).ilike(pattern),
                        cast(User.id, String).ilike(pattern),
                    )
                )

            total_rows = int(
                await session.scalar(
                    select(func.count(WebAccount.id))
                    .join(User, User.id == WebAccount.user_id)
                    .where(*filters)
                ) or 0
            )

            result = await session.execute(
                select(WebAccount, User, InvCustomer)
                .join(User, User.id == WebAccount.user_id)
                .outerjoin(
                    InvCustomer,
                    InvCustomer.web_account_id == WebAccount.id,
                )
                .where(*filters)
                .order_by(WebAccount.id.desc())
                .offset(offset)
                .limit(page_size)
            )

            site_rows = [
                {
                    "account": account,
                    "user": user,
                    "customer": customer,
                }
                for account, user, customer in result.all()
            ]

        elif tab == "bots":
            filters = [
                or_(
                    User.telegram_id.is_not(None),
                    User.bale_id.is_not(None),
                )
            ]

            if q:
                filters.append(
                    or_(
                        User.username.ilike(pattern),
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        User.phone_number.ilike(pattern),
                        cast(User.id, String).ilike(pattern),
                        cast(User.telegram_id, String).ilike(pattern),
                        cast(User.bale_id, String).ilike(pattern),
                    )
                )

            total_rows = int(
                await session.scalar(
                    select(func.count(User.id)).where(*filters)
                ) or 0
            )

            result = await session.scalars(
                select(User)
                .where(*filters)
                .order_by(User.id.desc())
                .offset(offset)
                .limit(page_size)
            )
            bot_rows = list(result.all())

    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = min(page, total_pages)

    return templates.TemplateResponse(
        "account_admin_users.html",
        {
            "request": request,
            "tab": tab,
            "q": q,
            "csrf_token": _customer_links_csrf_token(request),
            "reset_error": None,
            "reset_message": None,
            "reset_url": None,
            "reset_phone_number": "",
            "expires_minutes": RESET_TOKEN_MINUTES,
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "counts": counts,
            "customer_rows": customer_rows,
            "site_rows": site_rows,
            "bot_rows": bot_rows,
        },
    )

