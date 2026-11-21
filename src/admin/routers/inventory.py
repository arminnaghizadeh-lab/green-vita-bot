from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.auth import SESSION_KEY, require_authentication
from src.admin.dependencies import get_session
from src.db.models.inventory import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryMovement,
    InventoryWarehouse,
)
from src.invoices.models import Invoice, InvProduct

router = APIRouter()
templates = Jinja2Templates(directory="src/admin/templates")

DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def name_key(value):
    return " ".join(
        str(value or "").translate(DIGITS).casefold().split()
    )


def tracked(data):
    value = (data or {}).get("track_inventory")
    return value is True or str(value or "").lower() in (
        "1", "true", "yes", "on"
    )


def decimal_value(value, label="مقدار", allow_zero=False):
    raw = str(value if value is not None else "0").translate(DIGITS)
    raw = raw.replace(",", "").replace("٬", "").replace("،", "").replace(" ", "")
    try:
        number = Decimal(raw or "0")
    except InvalidOperation:
        raise HTTPException(400, f"{label} معتبر نیست.")

    if not number.is_finite():
        raise HTTPException(400, f"{label} معتبر نیست.")

    if number < 0 or (number == 0 and not allow_zero):
        raise HTTPException(400, f"{label} باید مثبت باشد.")

    if number.as_tuple().exponent < -3:
        raise HTTPException(400, f"{label} حداکثر سه رقم اعشار می‌تواند داشته باشد.")

    return number.quantize(Decimal("0.001"))


def money(value):
    return Decimal(value).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )


def valid_date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise HTTPException(400, "تاریخ معتبر نیست.")


def page_auth(request):
    return require_authentication(request)


def api_auth(request):
    if not request.session.get(SESSION_KEY):
        raise HTTPException(401, "نشست مدیر معتبر نیست.")


def product_data(product):
    return product.data if isinstance(product.data, dict) else {}


def product_lookup(products):
    result = {}

    # Register all current names first.
    for product in products:
        data = product_data(product)
        for candidate in (data.get("name"), product.name):
            key = name_key(candidate)
            if key:
                result[key] = product

    # Historical names are fallback aliases.
    for product in products:
        aliases = product_data(product).get("legacy_names")
        if isinstance(aliases, list):
            for alias in aliases:
                key = name_key(alias)
                if key:
                    result.setdefault(key, product)

    return result


async def locked_products(session, ids):
    result = await session.scalars(
        select(InvProduct)
        .where(InvProduct.id.in_(ids))
        .order_by(InvProduct.id)
        .with_for_update()
    )
    products = list(result)

    if len({p.id for p in products}) != len(set(ids)):
        raise HTTPException(404, "یک یا چند کالا در فهرست محصولات پیدا نشد.")

    return {p.id: p for p in products}


async def stock_balance(session, product_id, warehouse="main"):
    value = await session.scalar(
        select(func.coalesce(func.sum(InventoryMovement.quantity_delta), 0))
        .where(
            InventoryMovement.product_id == product_id,
            InventoryMovement.warehouse == warehouse,
        )
    )
    return Decimal(value or 0)


def json_document(doc):
    return {
        "id": doc.id,
        "document_no": doc.document_no,
        "document_type": doc.document_type,
        "document_date": doc.document_date.isoformat(),
        "party_name": doc.party_name,
        "reference_invoice_no": doc.reference_invoice_no,
        "description": doc.description,
        "total_amount": str(doc.total_amount),
        "status": doc.status,
    }


# ---------------------------------------------------------
# PAGES
# ---------------------------------------------------------

@router.get("/inventory/")
async def inventory_home(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = page_auth(request)
    if redirect:
        return redirect

    products = (
        await session.scalars(
            select(InvProduct).order_by(InvProduct.name)
        )
    ).all()

    balances = (
        await session.execute(
            select(
                InventoryMovement.product_id,
                InventoryMovement.warehouse,
                func.sum(InventoryMovement.quantity_delta),
            ).group_by(
                InventoryMovement.product_id,
                InventoryMovement.warehouse,
            )
        )
    ).all()

    balance_map = {}
    for product_id, warehouse, quantity in balances:
        balance_map[(product_id, warehouse)] = Decimal(quantity or 0)

    warehouse_rows = (
        await session.scalars(
            select(InventoryWarehouse).order_by(InventoryWarehouse.code)
        )
    ).all()
    warehouse_names = {
        str(item.code): item.name for item in warehouse_rows
    }

    rows = []
    for product in products:
        data = product_data(product)
        if not tracked(data):
            continue

        warehouse_balances = {}
        available_total = Decimal("0")

        for warehouse in warehouse_rows:
            code = str(warehouse.code)
            quantity = balance_map.get(
                (product.id, code), Decimal("0")
            )
            warehouse_balances[code] = str(quantity.normalize())

            if warehouse.is_active and code != "quarantine":
                available_total += quantity

        minimum = Decimal(str(data.get("min_stock") or "0"))

        rows.append({
            "id": product.id,
            "name": data.get("name") or product.name,
            "unit": data.get("unit") or "",
            "balances": warehouse_balances,
            "minimum": str(minimum.normalize()),
            "low": available_total <= minimum,
        })

    movements = (
        await session.scalars(
            select(InventoryMovement)
            .order_by(InventoryMovement.id.desc())
            .limit(15)
        )
    ).all()

    return templates.TemplateResponse(
        "finance/inventory.html",
        {
            "request": request,
            "app_name": "Green Vita",
            "products": rows,
            "movements": movements,
            "warehouses": warehouse_rows,
            "warehouse_names": warehouse_names,
            "tracked_count": len(rows),
            "purchase_url": "/finance/purchases/new/",
            "return_url": "/finance/sales-returns/new/",
        },
    )


@router.get("/purchases/")
async def purchases_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = page_auth(request)
    if redirect:
        return redirect

    docs = (
        await session.scalars(
            select(InventoryDocument)
            .where(InventoryDocument.document_type == "purchase")
            .order_by(InventoryDocument.id.desc())
            .limit(100)
        )
    ).all()

    return templates.TemplateResponse(
        "finance/purchases.html",
        {"request": request, "app_name": "Green Vita", "documents": docs},
    )


@router.get("/purchases/new/")
async def purchase_form(request: Request):
    redirect = page_auth(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "finance/purchase_new.html",
        {"request": request, "app_name": "Green Vita"},
    )


@router.get("/sales-returns/")
async def returns_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    redirect = page_auth(request)
    if redirect:
        return redirect

    docs = (
        await session.scalars(
            select(InventoryDocument)
            .where(InventoryDocument.document_type == "sales_return")
            .order_by(InventoryDocument.id.desc())
            .limit(100)
        )
    ).all()

    return templates.TemplateResponse(
        "finance/sales_returns.html",
        {"request": request, "app_name": "Green Vita", "documents": docs},
    )


@router.get("/sales-returns/new/")
async def return_form(request: Request):
    redirect = page_auth(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "finance/sales_return_new.html",
        {"request": request, "app_name": "Green Vita"},
    )


# ---------------------------------------------------------
# INVENTORY QUERIES
# ---------------------------------------------------------

@router.get("/api/products")
async def inventory_products(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    products = (
        await session.scalars(select(InvProduct).order_by(InvProduct.name))
    ).all()

    warehouse_rows = (
        await session.scalars(
            select(InventoryWarehouse)
            .where(InventoryWarehouse.is_active.is_(True))
            .order_by(InventoryWarehouse.name, InventoryWarehouse.code)
        )
    ).all()

    balance_rows = (
        await session.execute(
            select(
                InventoryMovement.product_id,
                InventoryMovement.warehouse,
                func.coalesce(func.sum(InventoryMovement.quantity_delta), 0),
            ).group_by(
                InventoryMovement.product_id,
                InventoryMovement.warehouse,
            )
        )
    ).all()

    balance_map = {
        (product_id, str(warehouse)): Decimal(quantity or 0)
        for product_id, warehouse, quantity in balance_rows
    }

    result = []
    for product in products:
        data = product_data(product)
        if not tracked(data):
            continue

        warehouse_balances = {
            str(warehouse.code): str(
                balance_map.get((product.id, str(warehouse.code)), Decimal("0"))
            )
            for warehouse in warehouse_rows
        }

        main = balance_map.get((product.id, "main"), Decimal("0"))
        quarantine = balance_map.get((product.id, "quarantine"), Decimal("0"))

        result.append({
            "id": product.id,
            "name": data.get("name") or product.name,
            "unit": data.get("unit") or "",
            "price": str(data.get("price") or "0"),
            "minimum": str(data.get("min_stock") or "0"),
            "main": str(main),
            "quarantine": str(quarantine),
            "balances": warehouse_balances,
        })

    return {
        "warehouses": [
            {"code": row.code, "name": row.name}
            for row in warehouse_rows
        ],
        "products": result,
    }


@router.get("/api/kardex/{product_id}")
async def inventory_kardex(
    product_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    product = await session.get(InvProduct, product_id)
    if not product or not tracked(product_data(product)):
        raise HTTPException(404, "کالای انباردار پیدا نشد.")

    rows = (
        await session.scalars(
            select(InventoryMovement)
            .where(InventoryMovement.product_id == product_id)
            .order_by(
                InventoryMovement.movement_date,
                InventoryMovement.id,
            )
        )
    ).all()

    warehouse_rows = (
        await session.scalars(select(InventoryWarehouse))
    ).all()
    warehouse_names = {str(item.code): item.name for item in warehouse_rows}

    running = {}
    result = []

    for row in rows:
        code = str(row.warehouse)
        running[code] = running.get(code, Decimal("0")) + Decimal(row.quantity_delta)
        result.append({
            "date": row.movement_date.isoformat(),
            "warehouse": code,
            "warehouse_name": warehouse_names.get(code, code),
            "quantity": str(row.quantity_delta),
            "balance": str(running[code]),
            "source": row.source_type,
            "source_id": row.source_id,
            "description": row.description or "",
            "unit_cost": str(row.unit_cost),
        })

    return {
        "product": product_data(product).get("name") or product.name,
        "movements": result,
    }


# ---------------------------------------------------------
# PURCHASE INVOICE
# ---------------------------------------------------------

@router.post("/api/purchases")
async def create_purchase(
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    supplier = str(body.get("supplier_name") or "").strip()
    if not supplier:
        raise HTTPException(400, "نام تأمین‌کننده را وارد کنید.")

    document_date = valid_date(body.get("document_date"))
    raw_lines = body.get("lines")

    if not isinstance(raw_lines, list) or not raw_lines:
        raise HTTPException(400, "حداقل یک ردیف خرید لازم است.")

    ids = [int(x.get("product_id") or 0) for x in raw_lines]
    if any(x <= 0 for x in ids):
        raise HTTPException(400, "کالای یکی از ردیف‌ها مشخص نیست.")

    products = await locked_products(session, ids)
    prepared = []
    total = Decimal("0")

    for index, raw in enumerate(raw_lines, start=1):
        product = products[int(raw["product_id"])]
        data = product_data(product)

        warehouse = str(raw.get("warehouse") or "main").strip()
        warehouse_record = await session.get(InventoryWarehouse, warehouse)
        if not warehouse_record or not warehouse_record.is_active:
            raise HTTPException(
                400,
                detail=f"انبار انتخاب‌شده در ردیف {index} معتبر یا فعال نیست.",
            )

        if not tracked(data):
            raise HTTPException(
                400,
                detail=f"«{product.name}» کالای انباردار نیست.",
            )

        quantity = decimal_value(raw.get("quantity"), "تعداد")
        price = decimal_value(raw.get("unit_price"), "قیمت خرید", True)
        line_total = money(quantity * price)
        total += line_total

        prepared.append({
            "line_no": index,
            "product": product,
            "data": data,
            "quantity": quantity,
            "price": price,
            "line_total": line_total,
            "warehouse": warehouse,
        })

    doc = InventoryDocument(
        document_no=f"TMP-{uuid4().hex[:20]}",
        document_type="purchase",
        document_date=document_date,
        party_name=supplier[:200],
        description=str(body.get("description") or "").strip()[:2000] or None,
        total_amount=money(total),
        status="posted",
    )

    try:
        session.add(doc)
        await session.flush()
        doc.document_no = f"PUR-{doc.id:08d}"

        for item in prepared:
            product = item["product"]
            data = item["data"]
            quantity = item["quantity"]
            price = item["price"]
            index = item["line_no"]
            cost = money(price)

            session.add(
                InventoryDocumentLine(
                    document_id=doc.id,
                    line_no=index,
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    unit=str(data.get("unit") or "")[:40],
                    quantity=quantity,
                    unit_price=price,
                    unit_cost=cost,
                    line_total=item["line_total"],
                )
            )

            session.add(
                InventoryMovement(
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    movement_date=document_date,
                    warehouse=item["warehouse"],
                    quantity_delta=quantity,
                    unit_cost=cost,
                    source_type="purchase",
                    source_id=doc.id,
                    source_line=index,
                    description=f"خرید {doc.document_no}",
                )
            )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return {
        "ok": True,
        "document": json_document(doc),
        "message": "فاکتور خرید ثبت شد و موجودی افزایش یافت.",
    }


# ---------------------------------------------------------
# FINAL SALES INVOICES ELIGIBLE FOR RETURN
# ---------------------------------------------------------

@router.get("/api/final-sales")
async def final_sales(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    invoices = (
        await session.scalars(
            select(Invoice)
            .where(Invoice.status == "final")
            .order_by(Invoice.id.desc())
            .limit(500)
        )
    ).all()

    invoice_ids = [invoice.id for invoice in invoices]
    sale_line_keys = set()

    if invoice_ids:
        movement_rows = (
            await session.execute(
                select(
                    InventoryMovement.source_id,
                    InventoryMovement.source_line,
                ).where(
                    InventoryMovement.source_type == "sale_invoice",
                    InventoryMovement.source_id.in_(invoice_ids),
                )
            )
        ).all()
        sale_line_keys = {
            (invoice_id, line_no)
            for invoice_id, line_no in movement_rows
        }

    returned_rows = (
        await session.execute(
            select(
                InventoryDocument.reference_invoice_id,
                InventoryDocumentLine.reference_line_no,
                func.sum(InventoryDocumentLine.quantity),
            )
            .join(
                InventoryDocumentLine,
                InventoryDocumentLine.document_id == InventoryDocument.id,
            )
            .where(
                InventoryDocument.document_type == "sales_return",
                InventoryDocument.status == "posted",
            )
            .group_by(
                InventoryDocument.reference_invoice_id,
                InventoryDocumentLine.reference_line_no,
            )
        )
    ).all()

    returned_map = {
        (invoice_id, line_no): Decimal(quantity or 0)
        for invoice_id, line_no, quantity in returned_rows
    }

    products = (
        await session.scalars(select(InvProduct))
    ).all()

    product_map = product_lookup(products)

    result = []

    for invoice in invoices:
        data = invoice.data if isinstance(invoice.data, dict) else {}
        invoice_lines = []

        for index, row in enumerate(data.get("rows", []), start=1):
            if not isinstance(row, dict):
                continue

            if (invoice.id, index) not in sale_line_keys:
                continue

            key = name_key(row.get("n"))
            product = product_map.get(key)
            if not product or not tracked(product_data(product)):
                continue

            sold = decimal_value(row.get("q"), "تعداد فروش")
            already = returned_map.get((invoice.id, index), Decimal("0"))
            available = sold - already
            if available <= 0:
                continue

            invoice_lines.append({
                "line_no": index,
                "product_id": product.id,
                "product_name": row.get("n") or product.name,
                "unit": row.get("u") or "",
                "sold": str(sold),
                "returned": str(already),
                "available": str(available),
                "unit_price": str(row.get("p") or "0"),
            })

        if invoice_lines:
            customer = data.get("cust") or {}
            result.append({
                "id": invoice.id,
                "no": invoice.no,
                "date": data.get("date") or invoice.date_text,
                "customer": customer.get("name") or invoice.customer_name,
                "lines": invoice_lines,
            })

    return {"invoices": result}


# ---------------------------------------------------------
# SALES RETURN
# ---------------------------------------------------------

@router.post("/api/sales-returns")
async def create_sales_return(
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    invoice_id = int(body.get("invoice_id") or 0)
    if invoice_id <= 0:
        raise HTTPException(400, "فاکتور فروش اصلی را انتخاب کنید.")

    invoice = await session.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .with_for_update()
    )

    if not invoice or invoice.status != "final":
        raise HTTPException(409, "فاکتور اصلی باید نهایی و معتبر باشد.")

    raw_lines = body.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise HTTPException(400, "حداقل یک قلم برگشتی لازم است.")

    try:
        return_date = valid_date(body.get("document_date"))
    except HTTPException:
        raise

    invoice_data = invoice.data if isinstance(invoice.data, dict) else {}
    original_rows = invoice_data.get("rows", [])
    selected = {}
    total = Decimal("0")

    for raw in raw_lines:
        try:
            line_no = int(raw.get("reference_line_no"))
        except (TypeError, ValueError):
            raise HTTPException(400, "ردیف فاکتور اصلی نامعتبر است.")

        if line_no < 1 or line_no > len(original_rows) or line_no in selected:
            raise HTTPException(400, "ردیف فاکتور اصلی تکراری یا نامعتبر است.")

        original = original_rows[line_no - 1]
        if not isinstance(original, dict):
            raise HTTPException(400, "ردیف فاکتور اصلی معتبر نیست.")

        quantity = decimal_value(raw.get("quantity"), "تعداد برگشتی")
        condition = str(raw.get("condition") or "good")
        if condition not in ("good", "quarantine"):
            raise HTTPException(400, "وضعیت کالای برگشتی معتبر نیست.")

        selected[line_no] = {
            "original": original,
            "quantity": quantity,
            "condition": condition,
        }

    names = [str(x["original"].get("n") or "").strip() for x in selected.values()]
    products = (
        await session.scalars(
            select(InvProduct).order_by(InvProduct.id).with_for_update()
        )
    ).all()

    product_map = product_lookup(products)

    product_ids = set()
    prepared = []

    for line_no, item in selected.items():
        original = item["original"]
        name = str(original.get("n") or "").strip()
        product = product_map.get(name_key(name))

        if not product or not tracked(product_data(product)):
            raise HTTPException(
                409,
                detail=f"«{name}» کالای انباردار معتبر نیست.",
            )

        if product.id in product_ids:
            # Different original rows of a same product are supported,
            # but each original row is independently validated below.
            pass
        product_ids.add(product.id)

        sold = decimal_value(original.get("q"), "تعداد فروش")
        already = await session.scalar(
            select(func.coalesce(func.sum(InventoryDocumentLine.quantity), 0))
            .join(
                InventoryDocument,
                InventoryDocument.id == InventoryDocumentLine.document_id,
            )
            .where(
                InventoryDocument.reference_invoice_id == invoice.id,
                InventoryDocument.document_type == "sales_return",
                InventoryDocument.status == "posted",
                InventoryDocumentLine.reference_line_no == line_no,
            )
        )
        available = sold - Decimal(already or 0)

        if item["quantity"] > available:
            raise HTTPException(
                409,
                detail=(
                    f"مقدار برگشت «{name}» بیشتر از مقدار قابل برگشت است. "
                    f"مانده قابل برگشت: {available}."
                ),
            )

        original_sale = await session.scalar(
            select(InventoryMovement)
            .where(
                InventoryMovement.source_type == "sale_invoice",
                InventoryMovement.source_id == invoice.id,
                InventoryMovement.source_line == line_no,
            )
            .with_for_update()
        )

        if not original_sale:
            raise HTTPException(
                409,
                detail=(
                    f"برای «{name}» گردش خروج انبار در زمان فروش وجود ندارد؛ "
                    "این فاکتور احتمالاً قبل از فعال شدن انبار ثبت شده است."
                ),
            )

        price = decimal_value(original.get("p"), "قیمت فروش", True)
        unit_cost = Decimal(original_sale.unit_cost or 0)
        qty = item["quantity"]
        total += money(qty * price)

        prepared.append({
            "line_no": line_no,
            "product": product,
            "original": original,
            "quantity": qty,
            "condition": item["condition"],
            "unit_cost": unit_cost,
            "price": price,
            "line_total": money(qty * price),
        })

    doc = InventoryDocument(
        document_no=f"TMP-{uuid4().hex[:20]}",
        document_type="sales_return",
        document_date=return_date,
        party_name=str((invoice_data.get("cust") or {}).get("name") or invoice.customer_name)[:200],
        reference_invoice_id=invoice.id,
        reference_invoice_no=invoice.no,
        description=str(body.get("description") or "").strip()[:2000] or None,
        total_amount=money(total),
        status="posted",
    )

    try:
        session.add(doc)
        await session.flush()
        doc.document_no = f"SRT-{doc.id:08d}"

        for index, item in enumerate(prepared, start=1):
            product = item["product"]
            data = product_data(product)
            warehouse = (
                "main" if item["condition"] == "good" else "quarantine"
            )

            session.add(
                InventoryDocumentLine(
                    document_id=doc.id,
                    line_no=index,
                    reference_line_no=item["line_no"],
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    unit=str(item["original"].get("u") or data.get("unit") or "")[:40],
                    quantity=item["quantity"],
                    unit_price=item["price"],
                    unit_cost=item["unit_cost"],
                    line_total=item["line_total"],
                    condition=item["condition"],
                )
            )

            session.add(
                InventoryMovement(
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    movement_date=return_date,
                    warehouse=warehouse,
                    quantity_delta=item["quantity"],
                    unit_cost=item["unit_cost"],
                    source_type="sales_return",
                    source_id=doc.id,
                    source_line=index,
                    description=f"برگشت از فروش {invoice.no} - {doc.document_no}",
                )
            )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return {
        "ok": True,
        "document": json_document(doc),
        "message": "برگشت از فروش ثبت شد و گردش انبار ایجاد شد.",
    }


# ---------------------------------------------------------
# OPENING STOCK
# ---------------------------------------------------------

@router.post("/api/opening-stock")
async def create_opening_stock(
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    document_date = valid_date(body.get("document_date"))
    raw_lines = body.get("lines")

    if not isinstance(raw_lines, list) or not raw_lines:
        raise HTTPException(400, "حداقل یک کالا برای موجودی اول دوره لازم است.")

    ids = [int(x.get("product_id") or 0) for x in raw_lines]
    if any(x <= 0 for x in ids):
        raise HTTPException(400, "کالای یکی از ردیف‌ها معتبر نیست.")

    products = await locked_products(session, ids)
    prepared = []

    for index, raw in enumerate(raw_lines, start=1):
        product = products[int(raw["product_id"])]
        data = product_data(product)

        warehouse = str(raw.get("warehouse") or "main").strip()
        warehouse_record = await session.get(InventoryWarehouse, warehouse)
        if not warehouse_record or not warehouse_record.is_active:
            raise HTTPException(
                400,
                detail=f"انبار انتخاب‌شده برای «{product.name}» معتبر یا فعال نیست.",
            )

        if not tracked(data):
            raise HTTPException(400, f"«{product.name}» کالای انباردار نیست.")

        quantity = decimal_value(raw.get("quantity"), "موجودی اول دوره")
        cost = money(decimal_value(raw.get("unit_cost"), "بهای واحد", True))

        existing = await session.scalar(
            select(InventoryMovement.id)
            .where(InventoryMovement.product_id == product.id)
            .limit(1)
        )
        if existing:
            raise HTTPException(
                409,
                detail=f"برای «{product.name}» قبلاً گردش انبار ثبت شده است.",
            )

        prepared.append((index, product, data, quantity, cost, warehouse))

    doc = InventoryDocument(
        document_no=f"TMP-{uuid4().hex[:20]}",
        document_type="adjustment",
        document_date=document_date,
        description="موجودی اول دوره",
        total_amount=money(sum(q * c for _, _, _, q, c, _ in prepared)),
        status="posted",
    )

    try:
        session.add(doc)
        await session.flush()
        doc.document_no = f"OPN-{doc.id:08d}"

        for index, product, data, quantity, cost, warehouse in prepared:
            session.add(
                InventoryDocumentLine(
                    document_id=doc.id,
                    line_no=index,
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    unit=str(data.get("unit") or "")[:40],
                    quantity=quantity,
                    unit_price=cost,
                    unit_cost=cost,
                    line_total=money(quantity * cost),
                    condition="good",
                )
            )

            session.add(
                InventoryMovement(
                    product_id=product.id,
                    product_name=data.get("name") or product.name,
                    movement_date=document_date,
                    warehouse=warehouse,
                    quantity_delta=quantity,
                    unit_cost=cost,
                    source_type="opening_stock",
                    source_id=doc.id,
                    source_line=index,
                    description="موجودی اول دوره",
                )
            )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return {
        "ok": True,
        "document": json_document(doc),
        "message": "موجودی اول دوره ثبت شد.",
    }


# GV WAREHOUSE MANAGEMENT API V1

@router.get("/api/warehouses")
async def list_warehouses(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    rows = (
        await session.scalars(
            select(InventoryWarehouse).order_by(
                InventoryWarehouse.name,
                InventoryWarehouse.code,
            )
        )
    ).all()

    return {
        "warehouses": [
            {
                "code": row.code,
                "name": row.name,
                "is_active": row.is_active,
            }
            for row in rows
        ]
    }


@router.post("/api/warehouses")
async def create_warehouse(
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    name = str(body.get("name") or "").strip()
    if not name or len(name) > 100:
        raise HTTPException(400, "نام انبار باید بین ۱ تا ۱۰۰ نویسه باشد.")

    existing = (
        await session.scalars(select(InventoryWarehouse))
    ).all()

    if any(name_key(row.name) == name_key(name) for row in existing):
        raise HTTPException(409, "انبار دیگری با این نام وجود دارد.")

    warehouse = InventoryWarehouse(
        code=f"wh_{uuid4().hex[:12]}",
        name=name,
        is_active=True,
    )
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)

    return {
        "ok": True,
        "warehouse": {
            "code": warehouse.code,
            "name": warehouse.name,
            "is_active": warehouse.is_active,
        },
    }


@router.patch("/api/warehouses/{code}")
async def update_warehouse(
    code: str,
    body: dict,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    warehouse = await session.get(
        InventoryWarehouse,
        code,
        with_for_update=True,
    )
    if warehouse is None:
        raise HTTPException(404, "انبار پیدا نشد.")

    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name or len(name) > 100:
            raise HTTPException(400, "نام انبار باید بین ۱ تا ۱۰۰ نویسه باشد.")

        existing = (
            await session.scalars(
                select(InventoryWarehouse).where(
                    InventoryWarehouse.code != code
                )
            )
        ).all()

        if any(name_key(row.name) == name_key(name) for row in existing):
            raise HTTPException(409, "انبار دیگری با این نام وجود دارد.")

        warehouse.name = name

    if "is_active" in body:
        active = body["is_active"]
        if not isinstance(active, bool):
            raise HTTPException(400, "وضعیت انبار معتبر نیست.")

        if code in {"main", "quarantine"} and not active:
            raise HTTPException(
                409,
                "انبارهای سیستمی قابل غیرفعال‌سازی نیستند؛ فقط نام آن‌ها را تغییر دهید.",
            )

        if not active:
            if warehouse.is_active:
                other_active = await session.scalar(
                    select(func.count()).select_from(InventoryWarehouse).where(
                        InventoryWarehouse.is_active.is_(True),
                        InventoryWarehouse.code != code,
                    )
                )
                if int(other_active or 0) == 0:
                    raise HTTPException(409, "حداقل یک انبار باید فعال باقی بماند.")

            balance = await session.scalar(
                select(
                    func.coalesce(
                        func.sum(InventoryMovement.quantity_delta), 0
                    )
                ).where(InventoryMovement.warehouse == code)
            )
            if Decimal(balance or 0) != 0:
                raise HTTPException(
                    409,
                    "مانده موجودی این انبار صفر نیست؛ ابتدا موجودی آن را تعیین تکلیف کنید.",
                )

        warehouse.is_active = active

    await session.commit()
    await session.refresh(warehouse)

    return {
        "ok": True,
        "warehouse": {
            "code": warehouse.code,
            "name": warehouse.name,
            "is_active": warehouse.is_active,
        },
    }


@router.delete("/api/warehouses/{code}")
async def delete_warehouse(
    code: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    api_auth(request)

    warehouse = await session.get(
        InventoryWarehouse,
        code,
        with_for_update=True,
    )
    if warehouse is None:
        return {"ok": True}

    if code in {"main", "quarantine"}:
        raise HTTPException(
            409,
            "انبارهای سیستمی قابل حذف نیستند؛ فقط نام آن‌ها را تغییر دهید.",
        )

    has_movements = await session.scalar(
        select(InventoryMovement.id)
        .where(InventoryMovement.warehouse == code)
        .limit(1)
    )

    if has_movements:
        raise HTTPException(
            409,
            "این انبار سابقه گردش دارد و قابل حذف نیست؛ آن را غیرفعال کنید.",
        )

    await session.delete(warehouse)
    await session.commit()

    return {"ok": True}
