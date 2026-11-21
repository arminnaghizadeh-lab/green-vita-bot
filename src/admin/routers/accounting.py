from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import require_authentication
from src.admin.dependencies import get_session
from src.db.models.accounting import (
    AccountingAccount,
    AccountingJournal,
    AccountingJournalLine,
)
from src.invoices.models import InvCustomer

router = APIRouter()
templates = Jinja2Templates(directory="src/admin/templates")

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def _money(value) -> str:
    amount = Decimal(str(value or 0))
    return f"{int(amount):,}".translate(_FA)


def _balance(net, normal_balance: str) -> str:
    amount = Decimal(str(net or 0))
    if amount == 0:
        return "۰ (تسویه)"

    if normal_balance == "debit":
        side = "بدهکار" if amount > 0 else "بستانکار"
    else:
        side = "بستانکار" if amount < 0 else "بدهکار"

    return f"{_money(abs(amount))} {side}"


def _dates(from_date: str | None, to_date: str | None):
    today = date.today()
    start_default = today.replace(day=1)

    try:
        start = date.fromisoformat(from_date) if from_date else start_default
    except ValueError:
        start = start_default

    try:
        end = date.fromisoformat(to_date) if to_date else today
    except ValueError:
        end = today

    if start > end:
        start, end = end, start

    return start, end


def _page_auth(request: Request):
    return require_authentication(request)


def _valid_id(value):
    try:
        result = int(value)
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None


@router.get("/general-ledger/")
async def general_ledger(
    request: Request,
    from_date: str | None = None,
    to_date: str | None = None,
    account_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    redirect = _page_auth(request)
    if redirect:
        return redirect

    start, end = _dates(from_date, to_date)
    A = AccountingAccount
    L = AccountingJournalLine
    J = AccountingJournal

    opening_debit = func.coalesce(
        func.sum(case((J.entry_date < start, L.debit), else_=0)), 0
    )
    opening_credit = func.coalesce(
        func.sum(case((J.entry_date < start, L.credit), else_=0)), 0
    )
    period_debit = func.coalesce(
        func.sum(
            case(
                (and_(J.entry_date >= start, J.entry_date <= end), L.debit),
                else_=0,
            )
        ),
        0,
    )
    period_credit = func.coalesce(
        func.sum(
            case(
                (and_(J.entry_date >= start, J.entry_date <= end), L.credit),
                else_=0,
            )
        ),
        0,
    )

    stmt = (
        select(
            A.id.label("account_id"),
            A.code,
            A.name,
            A.normal_balance,
            opening_debit.label("opening_debit"),
            opening_credit.label("opening_credit"),
            period_debit.label("debit"),
            period_credit.label("credit"),
        )
        .select_from(A)
        .outerjoin(L, L.account_id == A.id)
        .outerjoin(
            J,
            and_(
                J.id == L.journal_id,
                J.status == "posted",
                J.entry_date <= end,
            ),
        )
        .where(A.is_active.is_(True), A.is_postable.is_(True))
        .group_by(A.id, A.code, A.name, A.normal_balance)
        .order_by(A.code)
    )

    result = await session.execute(stmt)
    summary_rows = []

    for row in result:
        opening_net = Decimal(row.opening_debit or 0) - Decimal(row.opening_credit or 0)
        debit = Decimal(row.debit or 0)
        credit = Decimal(row.credit or 0)
        closing_net = opening_net + debit - credit

        summary_rows.append(
            {
                "account_id": row.account_id,
                "code": row.code,
                "name": row.name,
                "normal_balance": row.normal_balance,
                "opening": _balance(opening_net, row.normal_balance),
                "debit": _money(debit),
                "credit": _money(credit),
                "closing": _balance(closing_net, row.normal_balance),
                "opening_net": opening_net,
            }
        )

    selected_id = _valid_id(account_id)
    selected_account = (
        await session.get(A, selected_id) if selected_id else None
    )
    if selected_account and not selected_account.is_postable:
        selected_account = None

    details = []
    if selected_account:
        summary = next(
            (r for r in summary_rows if r["account_id"] == selected_account.id),
            None,
        )
        running = summary["opening_net"] if summary else Decimal("0")

        detail_stmt = (
            select(L, J)
            .join(J, J.id == L.journal_id)
            .where(
                L.account_id == selected_account.id,
                J.status == "posted",
                J.entry_date >= start,
                J.entry_date <= end,
            )
            .order_by(J.entry_date, J.id, L.line_no)
        )

        for line, journal in (await session.execute(detail_stmt)).all():
            debit = Decimal(line.debit or 0)
            credit = Decimal(line.credit or 0)
            running += debit - credit
            details.append(
                {
                    "date": journal.entry_date.isoformat(),
                    "number": f"JV-{journal.id:06d}",
                    "description": line.description or journal.description,
                    "debit": _money(debit),
                    "credit": _money(credit),
                    "balance": _balance(running, selected_account.normal_balance),
                }
            )

    accounts = (
        await session.scalars(
            select(A).where(A.is_active.is_(True), A.is_postable.is_(True)).order_by(A.code)
        )
    ).all()

    return templates.TemplateResponse(
        "finance/general_ledger.html",
        {
            "request": request,
            "app_name": "Green Vita",
            "accounts": accounts,
            "summary_rows": summary_rows,
            "details": details,
            "selected_account": selected_account,
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "new_journal_url": "/finance/journal/new/",
        },
    )


@router.get("/subsidiary-ledger/")
async def subsidiary_ledger(
    request: Request,
    from_date: str | None = None,
    to_date: str | None = None,
    account_id: int | None = None,
    party_type: str | None = None,
    party_name: str | None = None,
    party_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    redirect = _page_auth(request)
    if redirect:
        return redirect

    start, end = _dates(from_date, to_date)
    selected_account_id = _valid_id(account_id)
    selected_party_id = _valid_id(party_id)
    A = AccountingAccount
    L = AccountingJournalLine
    J = AccountingJournal

    stmt = (
        select(A, L, J)
        .join(L, L.account_id == A.id)
        .join(J, J.id == L.journal_id)
        .where(
            A.is_postable.is_(True),
            J.status == "posted",
            J.entry_date <= end,
            L.party_name.is_not(None),
        )
        .order_by(A.code, L.party_type, L.party_name, J.entry_date, J.id, L.line_no)
    )

    if selected_account_id:
        stmt = stmt.where(A.id == selected_account_id)
    if party_type in ("customer", "supplier", "other"):
        stmt = stmt.where(L.party_type == party_type)
    if party_name:
        stmt = stmt.where(L.party_name == party_name)
    if party_id is not None:
        if selected_party_id:
            stmt = stmt.where(L.party_id == selected_party_id)
        else:
            stmt = stmt.where(L.party_id.is_(None))

    groups = {}

    for account, line, journal in (await session.execute(stmt)).all():
        kind = line.party_type or "other"
        key = (account.id, kind, line.party_id, line.party_name)

        item = groups.setdefault(
            key,
            {
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "normal_balance": account.normal_balance,
                "party_type": kind,
                "party_type_label": {
                    "customer": "مشتری",
                    "supplier": "تأمین‌کننده",
                    "other": "سایر",
                }.get(kind, "سایر"),
                "party_id": line.party_id,
                "party_name": line.party_name,
                "opening_debit": Decimal("0"),
                "opening_credit": Decimal("0"),
                "debit": Decimal("0"),
                "credit": Decimal("0"),
            },
        )

        debit = Decimal(line.debit or 0)
        credit = Decimal(line.credit or 0)

        if journal.entry_date < start:
            item["opening_debit"] += debit
            item["opening_credit"] += credit
        else:
            item["debit"] += debit
            item["credit"] += credit

    summary_rows = []
    for key, item in groups.items():
        opening_net = item["opening_debit"] - item["opening_credit"]
        closing_net = opening_net + item["debit"] - item["credit"]

        query = {
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "account_id": item["account_id"],
            "party_type": item["party_type"],
            "party_name": item["party_name"],
        }
        if item["party_id"] is not None:
            query["party_id"] = item["party_id"]

        item.update(
            {
                "opening": _balance(opening_net, item["normal_balance"]),
                "debit_text": _money(item["debit"]),
                "credit_text": _money(item["credit"]),
                "closing": _balance(closing_net, item["normal_balance"]),
                "url": "/finance/subsidiary-ledger/?" + urlencode(query),
            }
        )
        summary_rows.append(item)

    summary_rows.sort(
        key=lambda x: (x["account_code"], x["party_type"], x["party_name"])
    )

    selected_account = (
        await session.get(A, selected_account_id)
        if selected_account_id
        else None
    )
    details = []

    selected_summary = None
    if selected_account and party_name:
        wanted_type = party_type or "other"
        selected_summary = groups.get(
            (
                selected_account.id,
                wanted_type,
                selected_party_id,
                party_name,
            )
        )

        if selected_summary:
            running = (
                selected_summary["opening_debit"]
                - selected_summary["opening_credit"]
            )

            detail_stmt = (
                select(L, J)
                .join(J, J.id == L.journal_id)
                .where(
                    L.account_id == selected_account.id,
                    L.party_name == party_name,
                    L.party_type == wanted_type,
                    J.status == "posted",
                    J.entry_date >= start,
                    J.entry_date <= end,
                )
                .order_by(J.entry_date, J.id, L.line_no)
            )

            if party_id is not None:
                if selected_party_id:
                    detail_stmt = detail_stmt.where(L.party_id == selected_party_id)
                else:
                    detail_stmt = detail_stmt.where(L.party_id.is_(None))

            for line, journal in (await session.execute(detail_stmt)).all():
                debit = Decimal(line.debit or 0)
                credit = Decimal(line.credit or 0)
                running += debit - credit

                details.append(
                    {
                        "date": journal.entry_date.isoformat(),
                        "number": f"JV-{journal.id:06d}",
                        "description": line.description or journal.description,
                        "debit": _money(debit),
                        "credit": _money(credit),
                        "balance": _balance(running, selected_account.normal_balance),
                    }
                )

    accounts = (
        await session.scalars(
            select(A)
            .where(A.is_active.is_(True), A.is_postable.is_(True))
            .order_by(A.code)
        )
    ).all()

    return templates.TemplateResponse(
        "finance/subsidiary_ledger.html",
        {
            "request": request,
            "app_name": "Green Vita",
            "accounts": accounts,
            "summary_rows": summary_rows,
            "details": details,
            "selected_account": selected_account,
            "selected_party_name": party_name,
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "account_id": selected_account_id,
            "party_type": party_type or "",
            "new_journal_url": "/finance/journal/new/",
        },
    )


@router.get("/journal/new/")
async def new_journal_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = _page_auth(request)
    if redirect:
        return redirect

    accounts = (
        await session.scalars(
            select(AccountingAccount)
            .where(
                AccountingAccount.is_active.is_(True),
                AccountingAccount.is_postable.is_(True),
            )
            .order_by(AccountingAccount.code)
        )
    ).all()

    customers = (
        await session.scalars(select(InvCustomer).order_by(InvCustomer.name))
    ).all()

    account_options = [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "requires_party": a.requires_party,
        }
        for a in accounts
    ]

    customer_names = []
    for customer in customers:
        data = customer.data if isinstance(customer.data, dict) else {}
        name = str(data.get("name") or customer.name or "").strip()
        if name:
            customer_names.append(name)

    return templates.TemplateResponse(
        "finance/journal_new.html",
        {
            "request": request,
            "app_name": "Green Vita",
            "account_options": account_options,
            "customer_names": sorted(set(customer_names)),
            "today": date.today().isoformat(),
        },
    )


def _amount(value) -> Decimal:
    raw = str(value if value is not None else "0").translate(_DIGITS)
    for char in (",", "٬", "،", "\u00a0", " "):
        raw = raw.replace(char, "")
    try:
        amount = Decimal(raw or "0")
    except InvalidOperation as exc:
        raise ValueError("مبلغ واردشده معتبر نیست.") from exc

    if not amount.is_finite() or amount < 0:
        raise ValueError("مبلغ باید عددی مثبت یا صفر باشد.")
    if amount != amount.to_integral_value():
        raise ValueError("مبلغ باید به ریال کامل وارد شود.")
    return amount


def _normalize_name(value):
    return " ".join(
        str(value or "").translate(_DIGITS).casefold().split()
    )


@router.post("/journals/")
async def create_journal(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    if _page_auth(request):
        raise HTTPException(status_code=401, detail="نشست مدیر معتبر نیست.")

    try:
        entry_date = date.fromisoformat(str(body.get("entry_date") or ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="تاریخ سند معتبر نیست.")

    description = str(body.get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="شرح سند را وارد کنید.")

    raw_lines = body.get("lines")
    if not isinstance(raw_lines, list) or not 2 <= len(raw_lines) <= 50:
        raise HTTPException(
            status_code=400,
            detail="سند باید حداقل دو و حداکثر پنجاه ردیف داشته باشد.",
        )

    prepared = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    customers = None

    for index, raw in enumerate(raw_lines, start=1):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"ردیف {index} نامعتبر است.")

        account_id = _valid_id(raw.get("account_id"))
        account = await session.get(AccountingAccount, account_id) if account_id else None

        if not account or not account.is_active or not account.is_postable:
            raise HTTPException(
                status_code=400,
                detail=f"حساب انتخاب‌شده در ردیف {index} معتبر یا قابل ثبت نیست.",
            )

        try:
            debit = _amount(raw.get("debit"))
            credit = _amount(raw.get("credit"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"ردیف {index}: {exc}") from exc

        if (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise HTTPException(
                status_code=400,
                detail=f"در ردیف {index} فقط یکی از ستون‌های بدهکار یا بستانکار باید مبلغ داشته باشد.",
            )

        party_name = str(raw.get("party_name") or "").strip()[:200]
        party_type = str(raw.get("party_type") or "").strip()

        if party_name and party_type not in ("customer", "supplier", "other"):
            raise HTTPException(
                status_code=400,
                detail=f"نوع طرف حساب در ردیف {index} معتبر نیست.",
            )

        if party_name and not party_type:
            party_type = "other"

        if account.requires_party and not party_name:
            raise HTTPException(
                status_code=400,
                detail=f"برای حساب «{account.name}» در ردیف {index} باید طرف حساب مشخص شود.",
            )

        party_id = None
        if party_type == "customer" and party_name:
            if customers is None:
                customers = (
                    await session.scalars(select(InvCustomer))
                ).all()

            wanted = _normalize_name(party_name)
            for customer in customers:
                data = customer.data if isinstance(customer.data, dict) else {}
                customer_name = data.get("name") or customer.name
                if _normalize_name(customer_name) == wanted:
                    party_id = customer.id
                    party_name = str(customer_name).strip()[:200]
                    break

        total_debit += debit
        total_credit += credit

        prepared.append(
            {
                "line_no": index,
                "account_id": account.id,
                "description": str(raw.get("description") or "").strip()[:500] or None,
                "debit": debit,
                "credit": credit,
                "party_type": party_type or None,
                "party_id": party_id,
                "party_name": party_name or None,
            }
        )

    if total_debit <= 0 or total_debit != total_credit:
        raise HTTPException(
            status_code=400,
            detail=(
                "سند تراز نیست. جمع بدهکار و بستانکار باید برابر و بیشتر از صفر باشد. "
                f"بدهکار: {_money(total_debit)} ریال؛ بستانکار: {_money(total_credit)} ریال."
            ),
        )

    try:
        entry = AccountingJournal(
            entry_date=entry_date,
            description=description[:500],
            status="posted",
            total_debit=total_debit,
            total_credit=total_credit,
            posted_at=datetime.now(timezone.utc),
        )
        session.add(entry)
        await session.flush()

        for line in prepared:
            session.add(
                AccountingJournalLine(
                    journal_id=entry.id,
                    **line,
                )
            )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return {
        "ok": True,
        "id": entry.id,
        "number": f"JV-{entry.id:06d}",
        "message": "سند حسابداری با موفقیت ثبت قطعی شد.",
    }
