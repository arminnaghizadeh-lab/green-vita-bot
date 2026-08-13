"""User repository — عملیات دیتابیس مخصوص کاربران."""

from sqlalchemy import select

from src.db.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> tuple[User, bool]:
        """اگر کاربر وجود داشت برمی‌گرداند، وگرنه می‌سازد. خروجی: (کاربر, تازه_ساخته_شد)."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user, False

        user = await self.create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        return user, True

    async def list_admins(self) -> list[User]:
        stmt = select(User).where(User.is_admin.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
