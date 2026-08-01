import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_character_identity_resolver import (
    EventCharacterIdentityResolver,
)
from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_lowercase_preposition_is_not_name_part():
    candidates = EventCharacterIdentityResolver._canonical_candidates(
        "Handlung Arthur befreit seinen Halbbruder Orm "
        "aus dem Gefängnis. Produktion"
    )

    assert "Orm aus" not in candidates


def test_lowercase_verbs_are_not_name_parts():
    candidates = EventCharacterIdentityResolver._canonical_candidates(
        "Arthur kämpft gegen David. David hat Arthur Jr. entführt."
    )

    assert "Arthur kämpft" not in candidates
    assert "David hat" not in candidates


def test_valid_full_names_still_work():
    aliases = EventCharacterIdentityResolver.build_alias_map(
        "Besetzung Arthur Curry / Aquaman, "
        "Orm Marius, David Kane / Black Manta. "
        "Handlung Arthur kämpft gegen David."
    )

    assert aliases["arthur"] == "Arthur Curry"
    assert aliases["orm"] == "Orm Marius"
    assert aliases["david"] == "David Kane"


def test_rescue_keeps_orm_without_false_identity_expansion():
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
    assert "character:orm aus" not in keys


def test_real_cast_resolves_orm_to_orm_marius():
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
    assert "character:orm aus" not in keys
