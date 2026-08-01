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


def test_cast_candidates_do_not_merge_neighbors():
    text = (
        "Besetzung Arthur Curry / Aquaman, "
        "Orm Marius, David Kane / Black Manta. "
        "Handlung Arthur kämpft gegen David."
    )

    candidates = EventCharacterIdentityResolver._canonical_candidates(text)

    assert "Arthur Curry" in candidates
    assert "Orm Marius" in candidates
    assert "David Kane" in candidates
    assert "Arthur Curry David" not in candidates
    assert "David Kane Handlung" not in candidates


def test_compact_cast_row_is_read_pairwise():
    text = (
        "Besetzung Arthur Curry Orm Marius David Kane Handlung "
        "Arthur kämpft gegen David."
    )

    aliases = EventCharacterIdentityResolver.build_alias_map(text)

    assert aliases["arthur"] == "Arthur Curry"
    assert aliases["orm"] == "Orm Marius"
    assert aliases["david"] == "David Kane"


def test_event_result_uses_canonical_names():
    text = (
        "Besetzung Arthur Curry / Aquaman, "
        "Orm Marius, David Kane / Black Manta. "
        "Handlung [ Bearbeiten | Quelltext bearbeiten ] "
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis. "
        "Später erfahren sie, dass David Arthur Jr. entführt hat. "
        "In Necrus kämpft Arthur gegen David. "
        "Produktion [ Bearbeiten | Quelltext bearbeiten ]"
    )

    result = EventIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "character:orm marius" in keys
    assert "character:david kane" in keys
    assert "character:arthur jr" in keys

    assert not any("handlung" in key for key in keys)
    assert not any("arthur curry david" in key for key in keys)


def test_edges_are_rewritten_to_canonical_names():
    text = (
        "Besetzung Arthur Curry / Aquaman, David Kane / Black Manta. "
        "Handlung Arthur kämpft gegen David. Produktion"
    )

    result = EventIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    participant_keys = {
        edge["source_node_key"]
        for edge in result["edges"]
        if edge["edge_type"] == "participates_in"
    }

    assert "character:arthur curry" in participant_keys
    assert "character:david kane" in participant_keys
