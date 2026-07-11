import random
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Protocol

from dog_excuses.catalog import LEVELS, SITUATIONS_BY_ID
from dog_excuses.domain import GeneratedExcuse, LevelId
from dog_excuses.verdicts import verdict_for, verdict_seed


@dataclass(slots=True)
class Bag:
    remaining: list[int]
    last: int | None = None


class BagStore(Protocol):
    async def load_bag(self, key: str) -> Bag | None: ...

    async def save_bag(self, key: str, bag: Bag) -> None: ...

    async def load_last_indices(self) -> tuple[int, ...] | None: ...

    async def save_last_indices(self, indices: tuple[int, ...]) -> None: ...


class RandomSource(Protocol):
    def randint(self, a: int, b: int) -> int: ...

    def shuffle(self, x: MutableSequence[int]) -> None: ...


async def _draw(store: BagStore, key: str, size: int, rng: RandomSource) -> int:
    bag = await store.load_bag(key) or Bag([])
    if not bag.remaining:
        bag.remaining = list(range(size))
        rng.shuffle(bag.remaining)
        if size > 1 and bag.remaining[0] == bag.last:
            bag.remaining[0], bag.remaining[1] = bag.remaining[1], bag.remaining[0]
    value = bag.remaining.pop(0)
    bag.last = value
    await store.save_bag(key, bag)
    return value


async def generate_excuse(
    situation_id: str,
    level_id: LevelId,
    store: BagStore,
    rng: RandomSource | None = None,
) -> GeneratedExcuse:
    random_source = rng or random.SystemRandom()
    situation = SITUATIONS_BY_ID[situation_id]
    pool = situation.levels[level_id]
    prefix = f"{situation_id}:{level_id}"

    for _ in range(2):
        opener_idx = await _draw(store, f"{prefix}:opener", len(situation.openers), random_source)
        reason_idx = await _draw(store, f"{prefix}:reason", len(pool.reasons), random_source)
        finale_idx = await _draw(store, f"{prefix}:finale", len(situation.finales), random_source)
        indices = (opener_idx, reason_idx, finale_idx)
        if indices != await store.load_last_indices():
            break

    reason = pool.reasons[reason_idx]
    finale = situation.finales[finale_idx]
    level = LEVELS[level_id]
    jitter = {
        LevelId.REAL: 3,
        LevelId.CREATIVE: 8,
        LevelId.ABSURD: 10,
    }[level_id]
    raw_score = reason.weight + finale.weight + random_source.randint(-jitter, jitter)
    score = max(3, min(raw_score, level.cap))
    text = " ".join((situation.openers[opener_idx], reason.text, finale.text))
    await store.save_last_indices(indices)
    return GeneratedExcuse(
        situation_id=situation_id,
        level_id=level_id,
        text=text,
        score=score,
        verdict=verdict_for(
            score,
            situation.low_verdict,
            level_id,
            verdict_seed(indices, score),
        ),
        indices=indices,
    )


def combination_count() -> int:
    return sum(
        len(situation.openers)
        * len(situation.finales)
        * sum(len(pool.reasons) for pool in situation.levels.values())
        for situation in SITUATIONS_BY_ID.values()
    )


def fragment_count() -> int:
    return sum(
        len(situation.openers)
        + len(situation.finales)
        + sum(len(pool.reasons) for pool in situation.levels.values())
        for situation in SITUATIONS_BY_ID.values()
    )
