"""
Declarative base for all SQLAlchemy models.

هر مدل جدید باید از Base ارث‌بری کند تا هم Alembic و هم متادیتای
مشترک (created_at / updated_at) را به‌صورت یکسان داشته باشد.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class shared by all ORM models."""

    pass


class TimestampMixin:
    """Adds created_at / updated_at columns automatically."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
