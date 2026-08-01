import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_rescue_stops_before_aus_phrase():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Um herauszufinden, wo David sich versteckt, "
            "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis. "
            "Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:orm" in keys
    assert "character:orm aus dem gefängnis" not in keys


def test_victory_stops_before_location():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Arthur Curry besiegte Black Manta in Necrus "
            "mit dem schwarzen Dreizack. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "character:black manta" in keys
    assert "character:black manta in necrus" not in keys
    assert "location:necrus" in keys
    assert "artifact:schwarzen dreizack" in keys
    assert {"occurs_at", "uses"} <= edge_types


def test_real_world_bundle():
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

    assert "character:orm" in keys
    assert "character:david" in keys
    assert "character:arthur jr" in keys
    assert "location:necrus" in keys
    assert {"rescue", "kidnapping", "battle"} <= event_types
