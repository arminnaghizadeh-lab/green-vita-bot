from pathlib import Path
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, RedirectResponse, Response, HTMLResponse
from playwright.async_api import async_playwright
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .compat import get_session, require_admin
from .models import InvCustomer, Invoice, InvProduct
from src.db.models.inventory import InventoryMovement, InventoryWarehouse

STATIC = Path(__file__).parent / "static" / "invoice.html"
INVOICE_ADMIN_TEMPLATES = Jinja2Templates(directory="src/admin/templates")
KINDS = {"c": InvCustomer, "p": InvProduct, "i": Invoice}
STATUSES = {"draft", "final", "void"}

# صفحهٔ فاکتور (اگر لاگین نباشد به /login می‌رود)
page_router = APIRouter()


@page_router.get("/admin/invoices", include_in_schema=False)
async def invoice_page(request: Request):
    try:
        require_admin(request)
    except HTTPException:
        return RedirectResponse("/login", status_code=302)
    html = STATIC.read_text(encoding="utf-8")

    topbar = INVOICE_ADMIN_TEMPLATES.get_template(
        "partials/admin-topbar.html"
    ).render(request=request)

    sidebar = INVOICE_ADMIN_TEMPLATES.get_template(
        "partials/admin-sidebar.html"
    ).render(request=request)

    html = html.replace(
        "</head>",
        '<link rel="stylesheet" href="/static/css/gv-admin-redesign.css?v=gv-invoice-menu-v1"></head>',
        1
    )

    html = html.replace("<body>", "<body>" + sidebar + topbar, 1)
    return HTMLResponse(html)


# API (همه نیازمند ادمین)
api = APIRouter(prefix="/admin/api/invoices", dependencies=[Depends(require_admin)])

_T = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def num(v) -> float:
    s = str(v or "").translate(_T)
    for ch in ",٬،\u00a0 ":
        s = s.replace(ch, "")
    try:
        return float(s or 0)
    except ValueError:
        return 0.0


def payable(d: dict) -> int:
    s = sum(num(r.get("q")) * num(r.get("p")) for r in d.get("rows", []))
    dc = num(d.get("disc"))
    return round((s - dc) * (1 + num(d.get("vat")) / 100))


# GV INVOICE MASTER DATA REFERENCE PROTECTION V1
def _name_key(value) -> str:
    return " ".join(
        str(value or "").translate(_T).casefold().split()
    )


def _record_name_keys(record) -> set[str]:
    data = record.data if isinstance(record.data, dict) else {}
    candidates = [data.get("name"), record.name]

    aliases = data.get("legacy_names")
    if isinstance(aliases, list):
        candidates.extend(x for x in aliases if isinstance(x, str))

    return {
        _name_key(value)
        for value in candidates
        if _name_key(value)
    }


async def _is_referenced(
    s: AsyncSession,
    kind: str,
    name: str,
) -> bool:
    target = _name_key(name)
    if not target:
        return False

    invoices = (
        await s.scalars(select(Invoice.data))
    ).all()

    for invoice in invoices:
        if not isinstance(invoice, dict):
            continue

        if kind == "c":
            customer = invoice.get("cust")
            if (
                isinstance(customer, dict)
                and _name_key(customer.get("name")) == target
            ):
                return True

        elif kind == "p":
            rows = invoice.get("rows")
            if not isinstance(rows, list):
                continue

            for row in rows:
                if (
                    isinstance(row, dict)
                    and _name_key(row.get("n")) == target
                ):
                    return True

    return False


def _reference_error(kind: str, action: str) -> str:
    noun = "مشتری" if kind == "c" else "کالا یا خدمت"
    if action == "delete":
        return f"این {noun} در یک یا چند فاکتور استفاده شده و قابل حذف نیست."
    return f"نام این {noun} در فاکتورهای قبلی استفاده شده و قابل تغییر نیست."


# GV SALE INVENTORY TRANSACTION V1
def _inventory_enabled(data: dict) -> bool:
    value = data.get("track_inventory")
    return value is True or str(value or "").strip().lower() in {
        "1", "true", "yes", "on", "کالا", "انباردار"
    }


def _inventory_quantity(value) -> Decimal:
    raw = str(value if value is not None else "0").translate(_T)
    for char in (",", "٬", "،", "\u00a0", " "):
        raw = raw.replace(char, "")
    try:
        qty = Decimal(raw or "0")
    except InvalidOperation as exc:
        raise HTTPException(400, "تعداد یکی از کالاهای انباردار معتبر نیست.") from exc

    if not qty.is_finite() or qty <= 0:
        raise HTTPException(400, "تعداد کالای انباردار باید بیشتر از صفر باشد.")

    if qty.as_tuple().exponent < -3:
        raise HTTPException(400, "تعداد کالا حداکثر می‌تواند سه رقم اعشار داشته باشد.")

    return qty.quantize(Decimal("0.001"))


async def _post_sale_inventory(
    s: AsyncSession,
    invoice_id: int,
    invoice_data: dict,
) -> None:
    products = (
        await s.scalars(
            select(InvProduct).order_by(InvProduct.id).with_for_update()
        )
    ).all()

    product_by_name = {}

    # Current names take priority over historical aliases.
    for product in products:
        data = product.data if isinstance(product.data, dict) else {}
        for candidate in (data.get("name"), product.name):
            key = _name_key(candidate)
            if key:
                product_by_name[key] = product

    for product in products:
        data = product.data if isinstance(product.data, dict) else {}
        aliases = data.get("legacy_names")
        if isinstance(aliases, list):
            for alias in aliases:
                key = _name_key(alias)
                if key:
                    product_by_name.setdefault(key, product)

    warehouses = (
        await s.scalars(
            select(InventoryWarehouse).where(
                InventoryWarehouse.is_active.is_(True)
            )
        )
    ).all()
    warehouse_by_code = {str(item.code): item for item in warehouses}

    stock_lines = []
    required = {}

    for index, row in enumerate(invoice_data.get("rows", []), start=1):
        if not isinstance(row, dict):
            continue

        product = product_by_name.get(_name_key(row.get("n")))
        if not product:
            continue

        data = product.data if isinstance(product.data, dict) else {}
        if not _inventory_enabled(data):
            continue

        warehouse = str(row.get("warehouse") or "main").strip()
        if warehouse not in warehouse_by_code:
            raise HTTPException(
                400,
                detail=f"انبار انتخاب‌شده برای «{product.name}» معتبر یا فعال نیست.",
            )

        qty = _inventory_quantity(row.get("q"))
        stock_key = (product.id, warehouse)
        required[stock_key] = required.get(stock_key, Decimal("0")) + qty
        stock_lines.append((index, product, row, qty, warehouse))

    average_costs = {}

    for (product_id, warehouse), requested in required.items():
        on_hand, stock_value = (
            await s.execute(
                select(
                    func.coalesce(func.sum(InventoryMovement.quantity_delta), 0),
                    func.coalesce(
                        func.sum(
                            InventoryMovement.quantity_delta
                            * InventoryMovement.unit_cost
                        ),
                        0,
                    ),
                ).where(
                    InventoryMovement.product_id == product_id,
                    InventoryMovement.warehouse == warehouse,
                )
            )
        ).one()

        on_hand = Decimal(on_hand or 0)
        stock_value = Decimal(stock_value or 0)

        product = next(p for p in products if p.id == product_id)
        warehouse_label = warehouse_by_code[warehouse].name

        if on_hand < requested:
            available = str(on_hand.normalize()).translate(
                str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹.")
            )
            needed = str(requested.normalize()).translate(
                str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹.")
            )
            raise HTTPException(
                409,
                detail=(
                    f"موجودی «{product.name}» در {warehouse_label} کافی نیست. "
                    f"موجودی: {available}؛ درخواست: {needed}."
                ),
            )

        average_costs[(product_id, warehouse)] = (
            (stock_value / on_hand).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            if on_hand > 0
            else Decimal("0")
        )

    for line_no, product, row, qty, warehouse in stock_lines:
        s.add(
            InventoryMovement(
                product_id=product.id,
                product_name=product.name,
                movement_date=date.today(),
                warehouse=warehouse,
                quantity_delta=-qty,
                unit_cost=average_costs[(product.id, warehouse)],
                source_type="sale_invoice",
                source_id=invoice_id,
                source_line=line_no,
                description=f"فروش فاکتور {invoice_data.get('no', '')}",
            )
        )


async def _reverse_sale_inventory(
    s: AsyncSession,
    invoice_id: int,
) -> None:
    existing_reversal = await s.scalar(
        select(InventoryMovement.id)
        .where(
            InventoryMovement.source_type == "sale_void",
            InventoryMovement.source_id == invoice_id,
        )
        .limit(1)
    )
    if existing_reversal:
        return

    original_moves = (
        await s.scalars(
            select(InventoryMovement)
            .where(
                InventoryMovement.source_type == "sale_invoice",
                InventoryMovement.source_id == invoice_id,
            )
            .order_by(InventoryMovement.source_line)
        )
    ).all()

    for movement in original_moves:
        s.add(
            InventoryMovement(
                product_id=movement.product_id,
                product_name=movement.product_name,
                movement_date=date.today(),
                warehouse=movement.warehouse,
                quantity_delta=-Decimal(movement.quantity_delta),
                unit_cost=movement.unit_cost,
                source_type="sale_void",
                source_id=invoice_id,
                source_line=movement.source_line,
                description=f"برگشت موجودی بابت ابطال فاکتور {invoice_id}",
            )
        )


async def _resolve_invoice_customer_id(
    s: AsyncSession,
    candidate_id,
    customer_name: str,
    *,
    fallback_id: int | None = None,
) -> int:
    target = _name_key(customer_name)
    if not target:
        raise HTTPException(400, "نام مشتری معتبر نیست.")

    if candidate_id not in (None, ""):
        if isinstance(candidate_id, bool):
            raise HTTPException(400, "شناسه مشتری معتبر نیست.")
        try:
            selected_id = int(str(candidate_id).strip())
        except (TypeError, ValueError):
            raise HTTPException(400, "شناسه مشتری معتبر نیست.")

        customer = await s.scalar(
            select(InvCustomer)
            .where(InvCustomer.id == selected_id)
            .with_for_update()
        )
        if customer is None:
            raise HTTPException(404, "پرونده مشتری پیدا نشد.")

        data = customer.data if isinstance(customer.data, dict) else {}
        stored_name = data.get("name") or customer.name

        if target not in _record_name_keys(customer):
            raise HTTPException(
                409,
                "نام مشتری با پرونده انتخاب‌شده یا نام تاریخی آن مطابقت ندارد.",
            )
        return customer.id

    if fallback_id is not None:
        previous = await s.get(InvCustomer, fallback_id)
        if previous is not None:
            data = previous.data if isinstance(previous.data, dict) else {}
            if target in _record_name_keys(previous):
                return previous.id

    customers = (await s.scalars(select(InvCustomer))).all()
    matches = []

    for customer in customers:
        data = customer.data if isinstance(customer.data, dict) else {}
        if target in _record_name_keys(customer):
            matches.append(customer)

    if len(matches) > 1:
        raise HTTPException(
            409,
            "چند پرونده مشتری با این نام وجود دارد؛ شناسه مشتری باید مشخص شود.",
        )

    if len(matches) == 1:
        return matches[0].id

    raise HTTPException(
        409,
        "پرونده این مشتری در بانک اطلاعات پیدا نشد؛ ابتدا مشتری را ثبت کنید.",
    )


@api.get("/bootstrap")
async def bootstrap(s: AsyncSession = Depends(get_session)):
    c = (await s.scalars(
        select(InvCustomer.data).order_by(InvCustomer.name)
    )).all()

    p = (await s.scalars(
        select(InvProduct.data).order_by(InvProduct.name)
    )).all()

    warehouse_rows = (await s.scalars(
        select(InventoryWarehouse)
        .where(InventoryWarehouse.is_active.is_(True))
        .order_by(InventoryWarehouse.name, InventoryWarehouse.code)
    )).all()
    w = [{"code": item.code, "name": item.name} for item in warehouse_rows]

    invoice_rows = (await s.scalars(
        select(Invoice).order_by(Invoice.id.desc())
    )).all()

    invoices = []
    for invoice in invoice_rows:
        item = dict(invoice.data) if isinstance(invoice.data, dict) else {}
        # Relational metadata is returned separately from the historical JSON snapshot.
        item["customer_id"] = invoice.customer_id
        invoices.append(item)

    nos = (await s.scalars(select(Invoice.no))).all()
    nums = [int(x) for x in nos if x.isdigit()]

    return {
        "c": c,
        "p": p,
        "w": w,
        "i": invoices,
        "n": (max(nums) if nums else 1000) + 1,
    }


@api.put("/{kind}/{oid}")
async def put_item(
    kind: str,
    oid: int,
    body: dict,
    s: AsyncSession = Depends(get_session),
):
    M = KINDS.get(kind)
    if not M:
        raise HTTPException(404, "unknown kind")
    if int(body.get("id", -1)) != oid:
        raise HTTPException(400, "id mismatch")

    vals = {"data": body, "updated_at": func.now()}

    if kind == "i":
        # Keep relational customer_id out of the historical JSON snapshot.
        supplied_customer_id = body.pop("customer_id", None)
        status = body.get("status")
        if status not in STATUSES:
            raise HTTPException(400, "bad status")

        old = await s.scalar(
            select(Invoice)
            .where(Invoice.id == oid)
            .with_for_update()
        )

        if old and old.status == "void":
            raise HTTPException(423, "void invoice is locked")

        if old and old.status == "final":
            if status == "final":
                if body == old.data:
                    return {"ok": True}
                raise HTTPException(
                    423,
                    detail="فاکتور نهایی قابل ویرایش نیست؛ برای اصلاح، برگشت یا سند اصلاحی ثبت کنید.",
                )

            if status != "void":
                raise HTTPException(
                    423,
                    detail="فاکتور نهایی فقط از مسیر ابطال قابل تغییر وضعیت است.",
                )

            # Keep the original invoice lines and amounts intact on void.
            safe_data = dict(old.data or {})
            safe_data["status"] = "void"
            body = safe_data
            vals["data"] = body
            await _reverse_sale_inventory(s, oid)

        elif status == "final":
            await _post_sale_inventory(s, oid, body)

        elif status == "void" and old is None:
            raise HTTPException(400, "فاکتور جدید را نمی‌توان مستقیم باطل کرد.")

        cust = body.get("cust") or {}
        customer_name = str(cust.get("name", "")).strip()[:200]
        invoice_no = str(body.get("no", "")).strip()[:32]

        if not invoice_no or not customer_name:
            raise HTTPException(400, "no and customer required")

        # Preserve the original relational link when voiding a final invoice.
        if old and old.status == "final" and status == "void":
            vals["customer_id"] = old.customer_id
        else:
            vals["customer_id"] = await _resolve_invoice_customer_id(
                s,
                supplied_customer_id,
                customer_name,
                fallback_id=old.customer_id if old else None,
            )

        vals.update(
            no=invoice_no,
            status=status,
            customer_name=customer_name,
            date_text=str(body.get("date", ""))[:16],
            payable=payable(body),
        )

    else:
        old = await s.scalar(
            select(M)
            .where(M.id == oid)
            .with_for_update()
        )

        vals["name"] = str(body.get("name", "")).strip()[:200]
        if not vals["name"]:
            raise HTTPException(400, "name required")

        if old:
            old_data = old.data if isinstance(old.data, dict) else {}
            old_name = old_data.get("name", "")

            if _name_key(old_name) != _name_key(vals["name"]):
                if await _is_referenced(s, kind, old_name):
                    raise HTTPException(
                        409,
                        detail=_reference_error(kind, "rename"),
                    )

                if kind == "p":
                    has_movement = await s.scalar(
                        select(InventoryMovement.id)
                        .where(InventoryMovement.product_id == oid)
                        .limit(1)
                    )
                    if has_movement:
                        raise HTTPException(
                            409,
                            detail="نام کالایی که گردش انبار دارد قابل تغییر نیست.",
                        )

            if kind == "p" and _inventory_enabled(old_data):
                if not _inventory_enabled(body):
                    balances = (
                        await s.execute(
                            select(
                                InventoryMovement.warehouse,
                                func.coalesce(
                                    func.sum(InventoryMovement.quantity_delta), 0
                                ),
                            )
                            .where(InventoryMovement.product_id == oid)
                            .group_by(InventoryMovement.warehouse)
                        )
                    ).all()

                    if any(Decimal(balance or 0) != 0 for _, balance in balances):
                        raise HTTPException(
                            409,
                            detail="تا وقتی موجودی کالا صفر نشده، نمی‌توان انبارداری آن را غیرفعال کرد.",
                        )

    stmt = (
        insert(M)
        .values(id=oid, **vals)
        .on_conflict_do_update(index_elements=[M.id], set_=vals)
    )

    try:
        await s.execute(stmt)
        await s.commit()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "duplicate invoice number")

    return {"ok": True}


@api.delete("/{kind}/{oid}")
async def delete_item(kind: str, oid: int, s: AsyncSession = Depends(get_session)):
    M = KINDS.get(kind)
    if not M:
        raise HTTPException(404, "unknown kind")
    if kind == "i":  # فاکتور حذف نمی‌شود، فقط ابطال
        raise HTTPException(405, "invoices cannot be deleted; void instead")

    record = await s.get(M, oid)
    if record:
        data = record.data if isinstance(record.data, dict) else {}
        name = data.get("name", "")

        if await _is_referenced(s, kind, name):
            raise HTTPException(
                409,
                detail=_reference_error(kind, "delete"),
            )

        if kind == "p":
            has_movement = await s.scalar(
                select(InventoryMovement.id)
                .where(InventoryMovement.product_id == oid)
                .limit(1)
            )
            if has_movement:
                raise HTTPException(
                    409,
                    detail="کالایی که سابقه گردش انبار دارد قابل حذف نیست.",
                )

    await s.execute(delete(M).where(M.id == oid))
    await s.commit()
    return {"ok": True}


@api.post("/pdf")
async def invoice_pdf(body: dict, request: Request):
    if not isinstance(body.get("cust"), dict) or not isinstance(body.get("rows"), list):
        raise HTTPException(400, "invalid invoice data")
    if body.get("status") not in (STATUSES | {"new"}):
        raise HTTPException(400, "invalid invoice status")

    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(401, "admin session required")

    base_url = "http://127.0.0.1:8000"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox"],
            )
            try:
                context = await browser.new_context()
                await context.add_cookies([{
                    "name": "session",
                    "value": session_cookie,
                    "url": base_url,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }])

                page = await context.new_page()
                await page.goto(
                    base_url + "/admin/invoices",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await page.wait_for_function(
                    "window.gvInvoiceReady === true",
                    timeout=20000,
                )
                await page.evaluate(
                    "(data) => window.gvLoadInvoiceForPdf(data)",
                    body,
                )
                await page.evaluate(
                    "() => document.fonts.ready.then(() => true)"
                )
                await page.evaluate("""async () => {
                    await Promise.all(Array.from(document.images).map(img => {
                        if (img.complete) return Promise.resolve();
                        return new Promise(resolve => {
                            img.onload = resolve;
                            img.onerror = resolve;
                        });
                    }));
                }""")
                await page.emulate_media(media="print")
                pdf_bytes = await page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                await browser.close()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="greenvita-invoice.pdf"',
                "Cache-Control": "no-store",
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "PDF generation failed")
