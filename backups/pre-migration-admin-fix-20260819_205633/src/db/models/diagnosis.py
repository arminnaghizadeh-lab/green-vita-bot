"""Diagnosis model — نتیجه‌ی هر تشخیص بیماری از روی عکس.

هر بار کاربر عکسی می‌فرستد و هوش مصنوعی تحلیل می‌کند، یک رکورد اینجا
ذخیره می‌شود — چه به یک گیاه ثبت‌شده متصل باشد چه نباشد (تشخیص سریع).
این جدول پایه‌ی «پرونده درمانی» گیاه در فاز بعد هم خواهد بود.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin
from src.db.models.visit_status import VisitStatus

if TYPE_CHECKING:
    from src.db.models.plant import Plant
    from src.db.models.user import User


class DiagnosisSeverity(str, enum.Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class Diagnosis(Base, TimestampMixin):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_id: Mapped[int | None] = mapped_column(
        ForeignKey("plants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # شناسه‌ی فایل عکس در تلگرام — برای دسترسی دوباره بدون نیاز به ذخیره باینری عکس
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # اطلاعاتی که خود کاربر قبل از تحلیل وارد کرده (اسم/نوع گیاه + توضیحات اضافه)
    plant_name_input: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disease_name: Mapped[str] = mapped_column(String(255), nullable=False, default="نامشخص")
    severity: Mapped[DiagnosisSeverity] = mapped_column(
    Enum(
        DiagnosisSeverity,
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
    ),
    default=DiagnosisSeverity.UNKNOWN,
    nullable=False,
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0..100

    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)  # هر علامت در یک خط
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)  # علت بروز بیماری/آفت
    treatment: Mapped[str | None] = mapped_column(Text, nullable=True)
    prevention: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    expert_visit_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # مدیریت درخواست ویزیت متخصص (پنل ادمین)
    visit_status: Mapped[VisitStatus] = mapped_column(
        Enum(
            VisitStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=VisitStatus.PENDING,
        nullable=False,
    )
    visit_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="diagnoses")
    plant: Mapped["Plant | None"] = relationship(back_populates="diagnoses")

    def __repr__(self) -> str:
        return (
            f"<Diagnosis id={self.id} disease={self.disease_name!r} "
            f"severity={self.severity} plant_id={self.plant_id}>"
        )
