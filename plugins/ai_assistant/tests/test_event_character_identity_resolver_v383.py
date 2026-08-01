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


def test_alias_map_prefers_parent_over_junior():
    text = (
        "Besetzung Arthur Curry / Aquaman, Orm Marius, David Kane. "
        "Handlung Arthur bekam einen Sohn Arthur Jr. "
        "Arthur kämpft gegen David."
    )

    aliases = EventCharacterIdentityResolver.build_alias_map(text)

    assert aliases["arthur"] == "Arthur Curry"
    assert aliases["david"] == "David Kane"
    assert aliases["orm"] == "Orm Marius"


def test_full_names_are_resolved_in_event_result():
    text = (
        "Besetzung Arthur Curry / Aquaman Orm Marius David Kane "
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
    assert "character:david kane" in keys
    assert "character:orm marius" in keys
    assert "character:arthur jr" in keys

    assert "character:arthur" not in keys
    assert "character:david" not in keys
    assert "character:orm" not in keys


def test_event_edges_use_resolved_keys():
    text = (
        "Arthur Curry David Kane "
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


def test_junior_name_stays_distinct():
    text = (
        "Arthur Curry David Kane "
        "Handlung Später erfahren sie, dass David Arthur Jr. "
        "entführt hat. Produktion"
    )

    result = EventIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" not in {
        key
        for key in keys
        if key == "character:arthur jr"
    }
    assert "character:arthur jr" in keys
