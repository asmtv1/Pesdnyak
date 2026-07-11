import json

import pytest
from sqlalchemy import select

from dog_excuses.db.base import Base
from dog_excuses.db.models import DailyMetric
from dog_excuses.db.repository import UserRepository, hash_user_id, increment_metric
from dog_excuses.db.session import create_engine_and_factory
from dog_excuses.domain import LevelId
from dog_excuses.generator import Bag


@pytest.fixture
async def database(tmp_path):  # type: ignore[no-untyped-def]
    engine, factory = create_engine_and_factory(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


def test_hmac_identity_is_stable_and_does_not_expose_id() -> None:
    first = hash_user_id(123456789, "secret")
    second = hash_user_id(123456789, "secret")
    assert first == second
    assert "123456789" not in first
    assert len(first) == 64


@pytest.mark.asyncio
async def test_selection_and_bag_survive_new_repository(database) -> None:  # type: ignore[no-untyped-def]
    repository = UserRepository(database, "a" * 64)
    await repository.set_selection("deadline", LevelId.CREATIVE)
    await repository.save_bag("deadline:creative:reason", Bag([1, 2, 3], 4))
    await repository.save_last_indices((1, 2, 3))

    restored = UserRepository(database, "a" * 64)
    assert await restored.get_selection() == ("deadline", LevelId.CREATIVE)
    bag = await restored.load_bag("deadline:creative:reason")
    assert bag == Bag([1, 2, 3], 4)
    assert await restored.load_last_indices() == (1, 2, 3)


@pytest.mark.asyncio
async def test_corrupted_bag_is_ignored(database) -> None:  # type: ignore[no-untyped-def]
    repository = UserRepository(database, "b" * 64)
    await repository.save_bag("key", Bag([1], 0))
    async with database.begin() as session:
        from dog_excuses.db.models import BagState

        row = await session.scalar(select(BagState))
        assert row is not None
        row.remaining = json.dumps(["broken"])
    assert await repository.load_bag("key") is None


@pytest.mark.asyncio
async def test_metrics_are_aggregated(database) -> None:  # type: ignore[no-untyped-def]
    await increment_metric(database, "generate", "deadline", LevelId.REAL)
    await increment_metric(database, "generate", "deadline", LevelId.REAL)
    async with database() as session:
        metric = await session.scalar(select(DailyMetric))
        assert metric is not None
        assert metric.count == 2
