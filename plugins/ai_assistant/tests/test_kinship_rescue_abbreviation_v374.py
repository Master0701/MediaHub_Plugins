import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_kinship_rescue_uses_only_character_name():
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
    assert "character:halbbruder orm" not in keys

    rescue_events = [
        node
        for node in result["nodes"]
        if node["node_type"] == "event"
        and node["metadata"]["event_type"] == "rescue"
    ]

    assert rescue_events[0]["metadata"]["kinship"] == "Halbbruder"


def test_jr_abbreviation_does_not_split_sentence():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Später erfahren sie, dass David Arthur Jr. "
            "entführt hat. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert "character:david" in keys
    assert "character:arthur jr" in keys
    assert "kidnapping" in event_types


def test_full_real_world_bundle():
    result = EventIntelligence().analyze(
        text=(
            "Handlung "
            "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis. "
            "Später erfahren sie, dass David Arthur Jr. entführt hat. "
            "In Necrus kämpft Arthur gegen David, um seinen Sohn zu retten. "
            "Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert {
        "character:arthur",
        "character:orm",
        "character:david",
        "character:arthur jr",
        "location:necrus",
    } <= keys

    assert {"rescue", "kidnapping", "battle"} <= event_types
