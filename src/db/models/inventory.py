from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    Numeric,
        String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class InventoryWarehouse(Base):
    __tablename__ = "inventory_warehouses"

    code: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class InventoryDocument(Base):
    __tablename__ = "inventory_documents"
    __table_args__ = (
        UniqueConstraint("document_no", name="uq_inventory_documents_no"),
        CheckConstraint(
            "document_type IN ('purchase','sales_return','adjustment')",
            name="ck_inventory_document_type",
        ),
        CheckConstraint(
            "status IN ('posted','void')",
            name="ck_inventory_document_status",
        ),
        Index("ix_inventory_documents_type_date", "document_type", "document_date"),
        Index("ix_inventory_documents_reference_invoice", "reference_invoice_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    document_no: Mapped[str] = mapped_column(String(40), nullable=False)
    document_type: Mapped[str] = mapped_column(String(24), nullable=False)
    document_date: Mapped[date] = mapped_column(Date, nullable=False)

    party_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    reference_invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("inv_invoices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reference_invoice_no: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False,
        default=Decimal("0"), server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False,
        default="posted", server_default="posted"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InventoryDocumentLine(Base):
    __tablename__ = "inventory_document_lines"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "line_no",
            name="uq_inventory_document_line_no",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_inventory_document_line_quantity",
        ),
        Index("ix_inventory_document_lines_document", "document_id"),
        Index("ix_inventory_document_lines_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_line_no: Mapped[int | None] = mapped_column(Integer, nullable=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("inv_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(40), nullable=False, default="", server_default=""
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False,
        default=Decimal("0"), server_default="0"
    )

    condition: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "source_line",
            "warehouse",
            name="uq_inventory_movement_source_line",
        ),
        CheckConstraint(
            "quantity_delta <> 0",
            name="ck_inventory_movement_nonzero",
        ),
        Index("ix_inventory_movements_product_date", "product_id", "movement_date"),
        Index("ix_inventory_movements_source", "source_type", "source_id"),
        Index("ix_inventory_movements_product_warehouse", "product_id", "warehouse"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("inv_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)

    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("inventory_warehouses.code", ondelete="RESTRICT"),
        nullable=False,
        default="main",
        server_default="main",
    )

    quantity_delta: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), nullable=False
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False,
        default=Decimal("0"), server_default="0"
    )

    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_line: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
