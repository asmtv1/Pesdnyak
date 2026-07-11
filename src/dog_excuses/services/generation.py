import asyncio
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dog_excuses.db.repository import UserRepository, increment_metric
from dog_excuses.domain import GeneratedExcuse, LevelId
from dog_excuses.generator import generate_excuse


class GenerationService:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def generate(
        self,
        user_hash: str,
        situation_id: str,
        level_id: LevelId,
        event: str = "generate",
    ) -> GeneratedExcuse:
        async with self._locks[user_hash]:
            repository = UserRepository(self.factory, user_hash)
            await repository.set_selection(situation_id, level_id)
            result = await generate_excuse(situation_id, level_id, repository)
            await increment_metric(self.factory, event, situation_id, level_id)
            return result
