from html import escape

from dog_excuses.catalog import LEVELS, SITUATIONS_BY_ID
from dog_excuses.domain import GeneratedExcuse, LevelId
from dog_excuses.verdicts import verdict_for, verdict_seed


def render_result(result: GeneratedExcuse) -> str:
    situation = SITUATIONS_BY_ID[result.situation_id]
    level = LEVELS[result.level_id]
    return (
        f"<b>{situation.emoji} {escape(situation.title)} · "
        f"{level.emoji} {escape(level.label)}</b>\n\n"
        f"{escape(result.text)}\n\n"
        f"<b>{result.score}% правдоподобности</b>\n"
        f"<i>{escape(result.verdict)}</i>"
    )


def encode_share(result: GeneratedExcuse) -> str:
    indices = ".".join(map(str, result.indices))
    return f"e:{result.situation_id}:{result.level_id.value}:{indices}:{result.score}"


def decode_share(query: str) -> GeneratedExcuse | None:
    try:
        marker, situation_id, level_raw, indices_raw, score_raw = query.split(":")
        if marker != "e" or situation_id not in SITUATIONS_BY_ID:
            return None
        level_id = LevelId(level_raw)
        indices = tuple(int(value) for value in indices_raw.split("."))
        if len(indices) != 3:
            return None
        opener_idx, reason_idx, finale_idx = indices
        situation = SITUATIONS_BY_ID[situation_id]
        pool = situation.levels[level_id]
        parts = (
            situation.openers[opener_idx],
            pool.reasons[reason_idx].text,
            situation.finales[finale_idx].text,
        )
        score = int(score_raw)
        if not 3 <= score <= LEVELS[level_id].cap:
            return None
    except (ValueError, IndexError):
        return None
    return GeneratedExcuse(
        situation_id=situation_id,
        level_id=level_id,
        text=" ".join(parts),
        score=score,
        verdict=verdict_for(
            score,
            situation.low_verdict,
            level_id,
            verdict_seed((opener_idx, reason_idx, finale_idx), score),
        ),
        indices=(opener_idx, reason_idx, finale_idx),
    )
