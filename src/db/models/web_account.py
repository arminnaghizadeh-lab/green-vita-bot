"""Web customer accounts, online diagnosis usage, and password reset tokens."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class WebAccount(Base, TimestampMixin):
    __tablename__ = "web_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Canonical Iranian mobile format, e.g. 09123456789.
    phone_number: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")


class WebDiagnosisUsage(Base, TimestampMixin):
    """One daily quota claim and its result for a web account.

    A failed attempt can be retried; processing/completed rows reserve the
    account's one successful diagnosis for the Tehran calendar day.
    """

    __tablename__ = "web_diagnosis_usages"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("web_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    plant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="processing",
        server_default="processing",
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id", "usage_date",
            name="uq_web_diagnosis_account_day",
        ),
        Index(
            "ix_web_diagnosis_account_created",
            "account_id", "created_at",
        ),
    )


class WebPasswordResetToken(Base, TimestampMixin):
    __tablename__ = "web_password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("web_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Only a SHA-256 hash is persisted; the raw token is shown to the admin
    # once so it can be sent to the customer.
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
