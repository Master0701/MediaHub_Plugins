import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_rescued_person_stops_before_aus():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Arthur befreit seinen Halbbruder Orm "
            "aus dem Gefängnis. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:orm" in keys
    assert not any("orm aus" in key for key in keys)


def test_long_following_sentence_is_not_part_of_name():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Um herauszufinden, wo David sich versteckt, "
            "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis. "
            "Die beiden treffen sich mit Kingfish. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:orm" in keys
    assert not any("kingfish" in key and "orm" in key for key in keys)


def test_valid_full_identity_resolution_still_works():
    result = EventIntelligence().analyze(
        text=(
            "Besetzung Arthur Curry / Aquaman, Orm Marius. "
            "Handlung Arthur befreit seinen Halbbruder Orm "
            "aus dem Gefängnis. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "character:orm marius" in keys
    assert not any("orm aus" in key for key in keys)


def test_other_preposition_boundaries():
    for phrase in (
        "Orm in Atlantis",
        "Orm mit Mera",
        "Orm nach Necrus",
        "Orm auf der Insel",
    ):
        cleaned = EventIntelligence._clean_event_person(phrase)
        assert cleaned == "Orm"
