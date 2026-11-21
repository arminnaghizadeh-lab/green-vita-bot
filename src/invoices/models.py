from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class _Common:
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )

    data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InvCustomer(_Common, Base):
    __tablename__ = "inv_customers"

    __table_args__ = (
        UniqueConstraint(
            "web_account_id",
            name="uq_inv_customers_web_account_id",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
    )

    web_account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("web_accounts.id", ondelete="SET NULL", name="fk_inv_customers_web_account_id_web_accounts"),
        nullable=True,
    )


class InvProduct(_Common, Base):
    __tablename__ = "inv_products"

    name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
    )


class Invoice(_Common, Base):
    __tablename__ = "inv_invoices"

    __table_args__ = (
        Index(
            "ix_inv_invoices_customer_id",
            "customer_id",
        ),
    )

    no: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(10),
        index=True,
        nullable=False,
    )

    customer_name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
    )

    customer_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("inv_customers.id", ondelete="RESTRICT", name="fk_inv_invoices_customer_id_inv_customers"),
        nullable=True,
    )

    date_text: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="",
    )

    payable: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
