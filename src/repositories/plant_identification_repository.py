"""PlantIdentification repository — عملیات دیتابیس مخصوص شناسایی گونه گیاه."""

from sqlalchemy import select

from src.db.models.plant_identification import PlantIdentification
from src.repositories.base import BaseRepository


class PlantIdentificationRepository(BaseRepository[PlantIdentification]):
    model = PlantIdentification

    async def list_by_user(self, user_id: int, limit: int = 20) -> list[PlantIdentification]:
        stmt = (
            select(PlantIdentification)
            .where(PlantIdentification.user_id == user_id)
            .order_by(PlantIdentification.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
