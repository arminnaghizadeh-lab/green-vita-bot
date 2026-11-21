from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import SESSION_KEY, require_authentication
from src.admin.dependencies import get_session
from src.invoices.models import Invoice, InvCustomer, InvProduct
from src.db.models.inventory import InventoryDocumentLine, InventoryMovement

router = APIRouter()
templates = Jinja2Templates(directory="src/admin/templates")


def fa_number(value):
    return str(value if value is not None else 0).translate(
        str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    )


@router.get("/")
async def finance_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    total_invoices = await session.scalar(
        select(func.count()).select_from(Invoice)
    ) or 0

    final_invoices = await session.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.status == "final"
        )
    ) or 0

    draft_invoices = await session.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.status == "draft"
        )
    ) or 0

    void_invoices = await session.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.status == "void"
        )
    ) or 0

    sales_total = await session.scalar(
        select(func.coalesce(func.sum(Invoice.payable), 0)).where(
            Invoice.status == "final"
        )
    ) or 0

    customers_count = await session.scalar(
        select(func.count()).select_from(InvCustomer)
    ) or 0

    products_count = await session.scalar(
        select(func.count()).select_from(InvProduct)
    ) or 0

    recent_result = await session.scalars(
        select(Invoice).order_by(Invoice.created_at.desc()).limit(10)
    )
    recent_invoices = list(recent_result)

    stats = {
        "total_invoices": fa_number(total_invoices),
        "final_invoices": fa_number(final_invoices),
        "draft_invoices": fa_number(draft_invoices),
        "void_invoices": fa_number(void_invoices),
        "sales_total": fa_number(sales_total),
        "customers_count": fa_number(customers_count),
        "products_count": fa_number(products_count),
    }

    return templates.TemplateResponse(
        "finance/index.html",
        {
            "request": request,
            "app_name": "Green Vita",
            "stats": stats,
            "recent_invoices": recent_invoices,
        },
    )


@router.get("/master-data/")
async def master_data_page(request: Request):
    redirect = require_authentication(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "finance/master_data.html",
        {"request": request, "app_name": "Green Vita"},
    )


# GV MASTER DATA API V1

def _master_key(value):
    digits = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return " ".join(str(value or "").translate(digits).casefold().split())


def _master_auth(request):
    if not request.session.get(SESSION_KEY):
        raise HTTPException(401, "نشست مدیر معتبر نیست.")


def _master_payload(record, kind):
    data = record.data if isinstance(record.data, dict) else {}
    result = {
        "id": record.id,
        "name": data.get("name") or record.name,
        "is_active": data.get("is_active", True) is not False,
        "legacy_names": data.get("legacy_names") or [],
    }
    if kind == "c":
        result.update({
            "phone": data.get("phone") or "",
            "addr": data.get("addr") or "",
            "web_account_linked": record.web_account_id is not None,
        })
    else:
        result.update({
            "unit": data.get("unit") or "",
            "price": data.get("price") or "0",
            "track_inventory": data.get("track_inventory", False),
            "min_stock": data.get("min_stock") or "0",
        })
    return result


async def _master_is_referenced(session, kind, record):
    data = record.data if isinstance(record.data, dict) else {}
    names = {
        _master_key(record.name),
        _master_key(data.get("name")),
    }
    names.update(
        _master_key(x)
        for x in data.get("legacy_names", [])
        if isinstance(x, str)
    )
    names.discard("")

    if kind == "p":
        movement = await session.scalar(
            select(InventoryMovement.id)
            .where(InventoryMovement.product_id == record.id)
            .limit(1)
        )
        document_line = await session.scalar(
            select(InventoryDocumentLine.id)
            .where(InventoryDocumentLine.product_id == record.id)
            .limit(1)
        )
        if movement or document_line:
            return True
    else:
        linked_invoice = await session.scalar(
            select(Invoice.id)
            .where(Invoice.customer_id == record.id)
            .limit(1)
        )
        if linked_invoice or record.web_account_id is not None:
            return True

    invoice_data = (
        await session.scalars(select(Invoice.data))
    ).all()

    for invoice in invoice_data:
        if not isinstance(invoice, dict):
            continue

        if kind == "c":
            customer = invoice.get("cust")
            if isinstance(customer, dict):
                if _master_key(customer.get("name")) in names:
                    return True
        else:
            rows = invoice.get("rows")
            if isinstance(rows, list):
                if any(
                    isinstance(row, dict)
                    and _master_key(row.get("n")) in names
                    for row in rows
                ):
                    return True

    return False


@router.get("/api/master-data")
async def master_data_list(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _master_auth(request)

    customers = (
        await session.scalars(select(InvCustomer).order_by(InvCustomer.name))
    ).all()
    products = (
        await session.scalars(select(InvProduct).order_by(InvProduct.name))
    ).all()

    return {
        "customers": [_master_payload(x, "c") for x in customers],
        "products": [_master_payload(x, "p") for x in products],
    }


@router.post("/api/master-data/{kind}")
async def master_data_create(
    kind: str,
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _master_auth(request)

    models = {"c": InvCustomer, "p": InvProduct}
    if kind not in models:
        raise HTTPException(404, "نوع اطلاعات پایه معتبر نیست.")

    raw_id = body.get("id")
    if isinstance(raw_id, bool):
        raise HTTPException(400, "شناسه معتبر نیست.")
    try:
        oid = int(raw_id)
    except (TypeError, ValueError):
        raise HTTPException(400, "شناسه معتبر نیست.")

    if oid <= 0 or await session.get(models[kind], oid):
        raise HTTPException(409, "شناسه نامعتبر یا تکراری است.")

    name = str(body.get("name") or "").strip()
    if not name or len(name) > 200:
        raise HTTPException(400, "نام باید بین ۱ تا ۲۰۰ نویسه باشد.")

    if kind == "c":
        data = {
            "name": name,
            "phone": str(body.get("phone") or "").strip()[:40],
            "addr": str(body.get("addr") or "").strip()[:1000],
            "is_active": True,
            "legacy_names": [],
        }
        record = InvCustomer(id=oid, name=name, data=data)
    else:
        tracked = body.get("track_inventory", False)
        if not isinstance(tracked, bool):
            raise HTTPException(400, "نوع کالا معتبر نیست.")

        data = {
            "name": name,
            "unit": str(body.get("unit") or "").strip()[:40],
            "price": str(body.get("price") or "0").strip(),
            "track_inventory": tracked,
            "min_stock": str(body.get("min_stock") or "0").strip(),
            "is_active": True,
            "legacy_names": [],
        }
        record = InvProduct(id=oid, name=name, data=data)

    session.add(record)
    await session.commit()
    return {"ok": True, "record": _master_payload(record, kind)}


@router.patch("/api/master-data/{kind}/{oid}")
async def master_data_update(
    kind: str,
    oid: int,
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _master_auth(request)

    models = {"c": InvCustomer, "p": InvProduct}
    if kind not in models:
        raise HTTPException(404, "نوع اطلاعات پایه معتبر نیست.")

    record = await session.get(models[kind], oid, with_for_update=True)
    if record is None:
        raise HTTPException(404, "رکورد موردنظر پیدا نشد.")

    data = dict(record.data) if isinstance(record.data, dict) else {}
    allowed = (
        {"name", "phone", "addr", "is_active"}
        if kind == "c"
        else {"name", "unit", "price", "track_inventory", "min_stock", "is_active"}
    )

    if set(body) - allowed:
        raise HTTPException(400, "فیلد ارسالی مجاز نیست.")

    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name or len(name) > 200:
            raise HTTPException(400, "نام باید بین ۱ تا ۲۰۰ نویسه باشد.")

        old_name = str(data.get("name") or record.name).strip()
        if _master_key(old_name) != _master_key(name):
            aliases = list(data.get("legacy_names") or [])
            if old_name and all(_master_key(x) != _master_key(old_name) for x in aliases):
                aliases.append(old_name)
            data["legacy_names"] = aliases[-50:]

        data["name"] = name
        record.name = name

    for key in allowed - {"name", "is_active"}:
        if key not in body:
            continue
        value = body[key]
        if key == "track_inventory":
            if not isinstance(value, bool):
                raise HTTPException(400, "نوع کالا معتبر نیست.")

            was_tracked = data.get("track_inventory") is True or str(
                data.get("track_inventory") or ""
            ).strip().lower() in {"1", "true", "yes", "on"}

            if was_tracked and not value:
                has_history = await session.scalar(
                    select(InventoryMovement.id)
                    .where(InventoryMovement.product_id == oid)
                    .limit(1)
                )
                if has_history:
                    raise HTTPException(
                        409,
                        "کالایی که سابقه گردش انبار دارد، نمی‌تواند به خدمت بدون انبار تبدیل شود.",
                    )

        elif key in {"phone", "addr", "unit", "price", "min_stock"}:
            value = str(value or "").strip()
            maximum = 1000 if key == "addr" else 100 if key in {"price", "min_stock"} else 40
            value = value[:maximum]
        data[key] = value

    if "is_active" in body:
        active = body["is_active"]
        if not isinstance(active, bool):
            raise HTTPException(400, "وضعیت فعال‌بودن معتبر نیست.")

        if kind == "p" and not active:
            balances = (
                await session.execute(
                    select(
                        InventoryMovement.warehouse,
                        func.coalesce(func.sum(InventoryMovement.quantity_delta), 0),
                    )
                    .where(InventoryMovement.product_id == oid)
                    .group_by(InventoryMovement.warehouse)
                )
            ).all()
            if any(Decimal(balance or 0) != 0 for _, balance in balances):
                raise HTTPException(
                    409,
                    "تا زمانی که موجودی کالا صفر نشده، غیرفعال‌سازی ممکن نیست.",
                )

        data["is_active"] = active

    record.data = data
    record.updated_at = func.now()
    await session.commit()
    return {"ok": True, "record": _master_payload(record, kind)}


@router.delete("/api/master-data/{kind}/{oid}")
async def master_data_delete(
    kind: str,
    oid: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _master_auth(request)

    models = {"c": InvCustomer, "p": InvProduct}
    if kind not in models:
        raise HTTPException(404, "نوع اطلاعات پایه معتبر نیست.")

    record = await session.get(models[kind], oid, with_for_update=True)
    if record is None:
        return {"ok": True, "deleted": True}

    referenced = await _master_is_referenced(session, kind, record)

    if kind == "p":
        balances = (
            await session.execute(
                select(
                    InventoryMovement.warehouse,
                    func.coalesce(func.sum(InventoryMovement.quantity_delta), 0),
                )
                .where(InventoryMovement.product_id == oid)
                .group_by(InventoryMovement.warehouse)
            )
        ).all()

        if any(Decimal(balance or 0) != 0 for _, balance in balances):
            raise HTTPException(
                409,
                "این کالا موجودی دارد؛ ابتدا موجودی آن را تعیین تکلیف کنید.",
            )

    if referenced:
        data = dict(record.data) if isinstance(record.data, dict) else {}
        data["is_active"] = False
        record.data = data
        record.updated_at = func.now()
        await session.commit()
        return {"ok": True, "deleted": False, "deactivated": True}

    await session.delete(record)
    await session.commit()
    return {"ok": True, "deleted": True, "deactivated": False}
