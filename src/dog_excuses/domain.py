from dataclasses import dataclass
from enum import StrEnum


class LevelId(StrEnum):
    REAL = "real"
    CREATIVE = "creative"
    ABSURD = "absurd"


@dataclass(frozen=True, slots=True)
class Level:
    id: LevelId
    label: str
    emoji: str
    cap: int


@dataclass(frozen=True, slots=True)
class WeightedText:
    text: str
    weight: int


@dataclass(frozen=True, slots=True)
class LevelPool:
    reasons: tuple[WeightedText, ...]


@dataclass(frozen=True, slots=True)
class Situation:
    id: str
    title: str
    emoji: str
    low_verdict: str
    openers: tuple[str, ...]
    causal_bridge: str
    finales: tuple[WeightedText, ...]
    levels: dict[LevelId, LevelPool]


@dataclass(frozen=True, slots=True)
class GeneratedExcuse:
    situation_id: str
    level_id: LevelId
    text: str
    score: int
    verdict: str
    indices: tuple[int, int, int]
