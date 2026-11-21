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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class AccountingAccount(Base):
    __tablename__ = "accounting_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('asset','liability','equity','revenue','expense')",
            name="ck_accounting_accounts_type",
        ),
        CheckConstraint(
            "normal_balance IN ('debit','credit')",
            name="ck_accounting_accounts_normal_balance",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounting_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )

    is_postable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_party: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AccountingJournal(Base):
    __tablename__ = "accounting_journal_entries"
    __table_args__ = (
        CheckConstraint(
            "total_debit = total_credit AND total_debit > 0",
            name="ck_accounting_journal_balanced",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="posted"
    )

    total_debit: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AccountingJournalLine(Base):
    __tablename__ = "accounting_journal_lines"
    __table_args__ = (
        UniqueConstraint(
            "journal_id", "line_no",
            name="uq_accounting_journal_line_no",
        ),
        CheckConstraint(
            "debit >= 0 AND credit >= 0 "
            "AND ((debit > 0 AND credit = 0) "
            "OR (credit > 0 AND debit = 0))",
            name="ck_accounting_journal_line_one_side",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_journal_entries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0")
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0")
    )

    party_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    party_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    party_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
