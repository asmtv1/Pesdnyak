from dog_excuses.domain import LevelId
from dog_excuses.verdicts import verdict_for


def test_creative_level_has_many_midrange_verdicts() -> None:
    variants = {
        verdict_for(48, "low", LevelId.CREATIVE, variant_seed) for variant_seed in range(100)
    }
    assert len(variants) == 12
    assert "Шансы 50 на 50 — решает виноватый взгляд собаки" in variants


def test_absurd_level_has_large_meme_pools() -> None:
    mid_variants = {
        verdict_for(23, "low", LevelId.ABSURD, variant_seed) for variant_seed in range(100)
    }
    low_variants = {
        verdict_for(12, "ситуационный приговор", LevelId.ABSURD, variant_seed)
        for variant_seed in range(100)
    }
    assert len(mid_variants) == 16
    assert len(low_variants) == 16
    assert any("мем" in verdict.lower() for verdict in mid_variants | low_variants)


def test_levels_use_different_verdict_styles_for_same_score() -> None:
    real = verdict_for(45, "low", LevelId.REAL, 7)
    creative = verdict_for(45, "low", LevelId.CREATIVE, 7)
    absurd = verdict_for(25, "low", LevelId.ABSURD, 7)
    assert len({real, creative, absurd}) == 3
