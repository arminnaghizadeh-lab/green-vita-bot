"""Conversation repository — تاریخچه گفتگوهای هوش مصنوعی."""

from sqlalchemy import select

from src.db.models.conversation import Conversation
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def list_by_user(self, user_id: int, limit: int = 20) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        # برای اینکه ترتیب گفتگو از قدیم به جدید باشد (مناسب کانتکست AI)
        return list(reversed(result.scalars().all()))
