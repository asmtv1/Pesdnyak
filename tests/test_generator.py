import random

import pytest

from dog_excuses.catalog import DOG_MARKERS
from dog_excuses.domain import LevelId
from dog_excuses.generator import SCORE_JITTER, Bag, generate_excuse


class MemoryStore:
    def __init__(self) -> None:
        self.bags: dict[str, Bag] = {}
        self.last_indices: tuple[int, ...] | None = None

    async def load_bag(self, key: str) -> Bag | None:
        bag = self.bags.get(key)
        return Bag(list(bag.remaining), bag.last) if bag else None

    async def save_bag(self, key: str, bag: Bag) -> None:
        self.bags[key] = Bag(list(bag.remaining), bag.last)

    async def load_last_indices(self) -> tuple[int, ...] | None:
        return self.last_indices

    async def save_last_indices(self, indices: tuple[int, ...]) -> None:
        self.last_indices = indices


@pytest.mark.asyncio
async def test_generated_excuse_has_three_sentences_and_valid_score() -> None:
    store = MemoryStore()
    result = await generate_excuse("late-work", LevelId.REAL, store, random.Random(42))
    assert len(result.text.split(". ")) == 3
    assert any(marker in result.text.lower() for marker in DOG_MARKERS)
    assert 3 <= result.score <= 92


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "cap"),
    [(LevelId.REAL, 92), (LevelId.CREATIVE, 70), (LevelId.ABSURD, 42)],
)
async def test_score_respects_level_cap(level: LevelId, cap: int) -> None:
    result = await generate_excuse("deadline", level, MemoryStore(), random.Random(1))
    assert 3 <= result.score <= cap


@pytest.mark.asyncio
async def test_bag_uses_every_reason_before_repeat() -> None:
    store = MemoryStore()
    rng = random.Random(7)
    reason_indices = []
    for _ in range(12):
        result = await generate_excuse("ghosted", LevelId.CREATIVE, store, rng)
        reason_indices.append(result.indices[1])
    assert len(set(reason_indices)) == 12


@pytest.mark.asyncio
async def test_full_result_never_repeats_immediately() -> None:
    store = MemoryStore()
    rng = random.Random(10)
    previous = None
    for _ in range(50):
        result = await generate_excuse("birthday", LevelId.ABSURD, store, rng)
        assert result.indices != previous
        previous = result.indices


@pytest.mark.asyncio
async def test_full_result_uses_every_combination_before_repeat() -> None:
    store = MemoryStore()
    rng = random.Random(15)
    combinations = {
        (
            await generate_excuse("late-work", LevelId.CREATIVE, store, rng)
        ).indices
        for _ in range(432)
    }
    assert len(combinations) == 432


def test_creative_and_absurd_scores_have_wider_jitter() -> None:
    assert SCORE_JITTER[LevelId.CREATIVE] == 16
    assert SCORE_JITTER[LevelId.ABSURD] == 18
