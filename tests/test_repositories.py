"""تست‌های src.repositories"""

import pytest

from src.repositories.plant_repository import PlantRepository
from src.repositories.user_repository import UserRepository

pytestmark = pytest.mark.asyncio


async def test_user_get_or_create_creates_new_user(db_session):
    repo = UserRepository(db_session)

    user, created = await repo.get_or_create(telegram_id=12345, username="armin")

    assert created is True
    assert user.telegram_id == 12345
    assert user.username == "armin"


async def test_user_get_or_create_returns_existing_user(db_session):
    repo = UserRepository(db_session)

    first_user, first_created = await repo.get_or_create(telegram_id=999)
    second_user, second_created = await repo.get_or_create(telegram_id=999)

    assert first_created is True
    assert second_created is False
    assert first_user.id == second_user.id


async def test_user_get_by_telegram_id_not_found_returns_none(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_telegram_id(999999)
    assert result is None


async def test_plant_list_by_owner(db_session):
    user_repo = UserRepository(db_session)
    plant_repo = PlantRepository(db_session)

    user, _ = await user_repo.get_or_create(telegram_id=555)
    await plant_repo.create(owner_id=user.id, name="مونستِرا")
    await plant_repo.create(owner_id=user.id, name="پتوس")

    plants = await plant_repo.list_by_owner(user.id)

    assert len(plants) == 2
    assert {p.name for p in plants} == {"مونستِرا", "پتوس"}


async def test_base_repository_update_and_delete(db_session):
    user_repo = UserRepository(db_session)
    user, _ = await user_repo.get_or_create(telegram_id=777, username="old")

    updated = await user_repo.update(user, username="new")
    assert updated.username == "new"

    await user_repo.delete(updated)
    result = await user_repo.get_by_id(user.id)
    assert result is None
