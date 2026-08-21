"""Reminder repository — یادآوری‌های آبیاری/کوددهی (منطق اجرا در فاز بعد)."""

from datetime import datetime

from sqlalchemy import select

from src.db.models.reminder import Reminder
from src.repositories.base import BaseRepository


class ReminderRepository(BaseRepository[Reminder]):
    model = Reminder

    async def list_by_plant(self, plant_id: int) -> list[Reminder]:
        stmt = select(Reminder).where(Reminder.plant_id == plant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_due(self, before: datetime) -> list[Reminder]:
        stmt = select(Reminder).where(
            Reminder.is_active.is_(True), Reminder.next_run_at <= before
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
