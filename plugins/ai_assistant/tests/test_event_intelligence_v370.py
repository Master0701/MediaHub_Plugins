import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_victory_event_with_location_and_artifact():
    result = EventIntelligence().analyze(
        text=(
            "Arthur Curry besiegte Black Manta in Necrus "
            "mit dem schwarzen Dreizack."
        ),
        source=SOURCE,
    )

    event_nodes = [
        node for node in result["nodes"]
        if node["node_type"] == "event"
    ]
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert result["event_count"] == 1
    assert event_nodes[0]["metadata"]["event_type"] == "victory"
    assert {
        "participates_in",
        "winner",
        "loser",
        "occurs_at",
        "uses",
    } <= edge_types


def test_rescue_and_kidnapping_events():
    result = EventIntelligence().analyze(
        text=(
            "Mera rettete Arthur Curry in Atlantis. "
            "David Kane entführte Arthur Jr. nach Necrus."
        ),
        source=SOURCE,
    )

    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert {"rescue", "kidnapping"} <= event_types


def test_discovery_and_creation_events():
    result = EventIntelligence().analyze(
        text=(
            "David Kane fand einen schwarzen Dreizack in Atlantis. "
            "Der schwarze Dreizack wurde von Kordax erschaffen."
        ),
        source=SOURCE,
    )

    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert {"discovery", "creation"} <= event_types


def test_events_are_confirmation_required():
    result = EventIntelligence().analyze(
        text="Arthur Curry kämpfte gegen Black Manta.",
        source=SOURCE,
    )

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        node["requires_confirmation"]
        for node in result["nodes"]
    )
