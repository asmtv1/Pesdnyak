import random

import pytest

from dog_excuses.bot.keyboards import levels_keyboard, situations_keyboard
from dog_excuses.bot.rendering import decode_share, encode_share, render_result
from dog_excuses.domain import LevelId
from dog_excuses.generator import Bag, generate_excuse


class MemoryStore:
    def __init__(self) -> None:
        self.bags: dict[str, Bag] = {}
        self.last: tuple[int, ...] | None = None

    async def load_bag(self, key: str) -> Bag | None:
        return self.bags.get(key)

    async def save_bag(self, key: str, bag: Bag) -> None:
        self.bags[key] = bag

    async def load_last_indices(self) -> tuple[int, ...] | None:
        return self.last

    async def save_last_indices(self, indices: tuple[int, ...]) -> None:
        self.last = indices


def test_keyboards_contain_all_options() -> None:
    assert sum(len(row) for row in situations_keyboard().inline_keyboard) == 8
    assert sum(len(row) for row in levels_keyboard("deadline").inline_keyboard) == 4


@pytest.mark.asyncio
async def test_share_payload_round_trip() -> None:
    result = await generate_excuse(
        "cancel-meeting", LevelId.CREATIVE, MemoryStore(), random.Random(5)
    )
    restored = decode_share(encode_share(result))
    assert restored == result
    assert "правдоподобности" in render_result(restored)


@pytest.mark.parametrize(
    "value", ["", "broken", "e:nope:real:1.1.1.1:20", "e:deadline:nope:1.1.1.1:20"]
)
def test_invalid_share_payload_is_rejected(value: str) -> None:
    assert decode_share(value) is None
