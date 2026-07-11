from dog_excuses.catalog import DOG_MARKERS, LEVELS, SITUATIONS, validate_catalog
from dog_excuses.domain import LevelId
from dog_excuses.generator import combination_count, fragment_count
from dog_excuses.verdicts import verdict_for


def test_catalog_shape_and_counts() -> None:
    validate_catalog()
    assert len(SITUATIONS) == 8
    assert fragment_count() == 344
    assert combination_count() == 8_928
    for situation in SITUATIONS:
        assert len(situation.openers) == 6
        assert len(situation.finales) == 6
        for level in LevelId:
            expected_reasons = 7 if level is LevelId.REAL else 12
            assert len(situation.levels[level].reasons) == expected_reasons


def test_level_caps() -> None:
    assert LEVELS[LevelId.REAL].cap == 92
    assert LEVELS[LevelId.CREATIVE].cap == 70
    assert LEVELS[LevelId.ABSURD].cap == 42


def test_verdict_thresholds() -> None:
    assert verdict_for(80, "low") == "Поверит даже кинолог"
    assert verdict_for(60, "low") == "Звучит как чистая правда"
    assert "50 на 50" in verdict_for(40, "low")
    assert verdict_for(20, "low") == "Рискованно, но за смелость уважают"
    assert verdict_for(19, "low") == "low"


def test_every_possible_result_mentions_a_dog() -> None:
    for situation in SITUATIONS:
        for pool in situation.levels.values():
            for reason in pool.reasons:
                assert any(marker in reason.text.lower() for marker in DOG_MARKERS)


def test_fragments_do_not_contain_known_bad_glue() -> None:
    for situation in SITUATIONS:
        for pool in situation.levels.values():
            for reason in pool.reasons:
                lowered = reason.text.lower()
                assert lowered.count("поэтому") <= 1
                assert "всю операцию" not in lowered
                assert reason.text.endswith(".")
                assert ". " not in reason.text


def test_all_8928_text_combinations_are_unique_and_well_formed() -> None:
    all_texts: set[str] = set()
    for situation in SITUATIONS:
        situation_texts: set[str] = set()
        for pool in situation.levels.values():
            for opener in situation.openers:
                for reason in pool.reasons:
                    for finale in situation.finales:
                        text = " ".join((opener, reason.text, finale.text))
                        assert len(text.split(". ")) == 3
                        assert any(marker in text.lower() for marker in DOG_MARKERS)
                        situation_texts.add(text)
        assert len(situation_texts) == 1_116
        all_texts.update(situation_texts)
    assert len(all_texts) == 8_928
