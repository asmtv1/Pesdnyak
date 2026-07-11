import hashlib
import hmac
import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dog_excuses.db.models import BagState, DailyMetric, UserState
from dog_excuses.domain import LevelId
from dog_excuses.generator import Bag


def hash_user_id(user_id: int, secret: str) -> str:
    return hmac.new(secret.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()


class UserRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession], user_hash: str) -> None:
        self.factory = factory
        self.user_hash = user_hash

    async def ensure_user(self) -> None:
        async with self.factory.begin() as session:
            statement = insert(UserState).values(user_hash=self.user_hash)
            await session.execute(statement.on_conflict_do_nothing(index_elements=["user_hash"]))

    async def set_selection(self, situation_id: str | None, level_id: LevelId | None) -> None:
        await self.ensure_user()
        async with self.factory.begin() as session:
            state = await session.get(UserState, self.user_hash)
            assert state is not None
            state.situation_id = situation_id
            state.level_id = level_id.value if level_id else None
            state.updated_at = datetime.now(UTC).replace(tzinfo=None)

    async def get_selection(self) -> tuple[str | None, LevelId | None]:
        async with self.factory() as session:
            state = await session.get(UserState, self.user_hash)
            if state is None:
                return None, None
            level = LevelId(state.level_id) if state.level_id else None
            return state.situation_id, level

    async def load_bag(self, key: str) -> Bag | None:
        async with self.factory() as session:
            row = await session.scalar(
                select(BagState).where(
                    BagState.user_hash == self.user_hash, BagState.bag_key == key
                )
            )
            if row is None:
                return None
            try:
                remaining = json.loads(row.remaining)
                if not isinstance(remaining, list) or not all(
                    isinstance(x, int) for x in remaining
                ):
                    return None
            except (json.JSONDecodeError, TypeError):
                return None
            return Bag(remaining=remaining, last=row.last_index)

    async def save_bag(self, key: str, bag: Bag) -> None:
        values = {
            "user_hash": self.user_hash,
            "bag_key": key,
            "remaining": json.dumps(bag.remaining),
            "last_index": bag.last,
        }
        async with self.factory.begin() as session:
            statement = insert(BagState).values(**values)
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=["user_hash", "bag_key"],
                    set_={"remaining": values["remaining"], "last_index": values["last_index"]},
                )
            )

    async def load_last_indices(self) -> tuple[int, ...] | None:
        async with self.factory() as session:
            state = await session.get(UserState, self.user_hash)
            if state is None or not state.last_indices:
                return None
            try:
                values = tuple(int(x) for x in state.last_indices.split(","))
            except ValueError:
                return None
            if len(values) not in (3, 4):
                return None
            return values

    async def save_last_indices(self, indices: tuple[int, ...]) -> None:
        await self.ensure_user()
        async with self.factory.begin() as session:
            state = await session.get(UserState, self.user_hash)
            assert state is not None
            state.last_indices = ",".join(map(str, indices))
            state.updated_at = datetime.now(UTC).replace(tzinfo=None)


async def increment_metric(
    factory: async_sessionmaker[AsyncSession],
    event: str,
    situation_id: str | None = None,
    level_id: LevelId | None = None,
) -> None:
    values = {
        "day": date.today(),
        "event": event,
        "situation_id": situation_id or "",
        "level_id": level_id.value if level_id else "",
        "count": 1,
    }
    async with factory.begin() as session:
        statement = insert(DailyMetric).values(**values)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=["day", "event", "situation_id", "level_id"],
                set_={"count": DailyMetric.count + 1},
            )
        )
