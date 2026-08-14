"""PlantIdentification model — نتیجه‌ی شناسایی گونه‌ی گیاه از روی عکس.

جدا از Diagnosis (که بیماری را تشخیص می‌دهد)، این جدول مخصوص شناسایی
خودِ گیاه و راهنمای نگهداری کامل آن است.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNKNOWN = "unknown"


class PlantIdentification(Base, TimestampMixin):
    __tablename__ = "plant_identifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # شناسه‌ی فایل عکس در تلگرام — برای دسترسی دوباره بدون نیاز به ذخیره باینری عکس
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)

    persian_name: Mapped[str] = mapped_column(String(255), nullable=False, default="نامشخص")
    scientific_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0..100
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
    Enum(
        DifficultyLevel,
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
    ),
    default=DifficultyLevel.UNKNOWN,
    nullable=False,
    )

    light_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    watering_schedule: Mapped[str | None] = mapped_column(Text, nullable=True)
    humidity: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[str | None] = mapped_column(Text, nullable=True)
    soil_mix: Mapped[str | None] = mapped_column(Text, nullable=True)
    fertilizer_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    potting_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    repotting_interval: Mapped[str | None] = mapped_column(Text, nullable=True)

    propagation_methods: Mapped[str | None] = mapped_column(Text, nullable=True)  # هر روش در یک خط
    common_pests: Mapped[str | None] = mapped_column(Text, nullable=True)  # هر مورد در یک خط
    common_diseases: Mapped[str | None] = mapped_column(Text, nullable=True)  # هر مورد در یک خط

    toxicity_pets: Mapped[str | None] = mapped_column(Text, nullable=True)
    toxicity_humans: Mapped[str | None] = mapped_column(Text, nullable=True)
    preventive_care_tips: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    expert_visit_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="plant_identifications")

    def __repr__(self) -> str:
        return (
            f"<PlantIdentification id={self.id} persian_name={self.persian_name!r} "
            f"confidence={self.confidence}>"
        )
