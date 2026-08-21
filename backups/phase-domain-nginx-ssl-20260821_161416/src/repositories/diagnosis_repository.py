"""Diagnosis repository — عملیات دیتابیس مخصوص نتایج تشخیص بیماری."""

from sqlalchemy import select

from src.db.models.diagnosis import Diagnosis
from src.repositories.base import BaseRepository


class DiagnosisRepository(BaseRepository[Diagnosis]):
    model = Diagnosis

    async def list_by_plant(self, plant_id: int, limit: int = 20) -> list[Diagnosis]:
        stmt = (
            select(Diagnosis)
            .where(Diagnosis.plant_id == plant_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(self, user_id: int, limit: int = 20) -> list[Diagnosis]:
        stmt = (
            select(Diagnosis)
            .where(Diagnosis.user_id == user_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
