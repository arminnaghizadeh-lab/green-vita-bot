"""Plant repository — عملیات دیتابیس مخصوص پرونده‌های گیاهان."""

from sqlalchemy import select

from src.db.models.plant import Plant
from src.repositories.base import BaseRepository


class PlantRepository(BaseRepository[Plant]):
    model = Plant

    async def list_by_owner(self, owner_id: int) -> list[Plant]:
        stmt = select(Plant).where(Plant.owner_id == owner_id).order_by(Plant.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(Plant)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
