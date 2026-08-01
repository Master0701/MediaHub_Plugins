import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_victory_separates_opponent_location_and_artifact():
    result = EventIntelligence().analyze(
        text=(
            "Arthur Curry besiegte Black Manta in Necrus "
            "mit dem schwarzen Dreizack."
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "character:arthur curry" in keys
    assert "character:black manta" in keys
    assert "location:necrus" in keys
    assert "artifact:schwarzen dreizack" in keys

    assert {
        "participates_in",
        "winner",
        "loser",
        "occurs_at",
        "uses",
    } <= edge_types


def test_battle_without_location_or_artifact_still_works():
    result = EventIntelligence().analyze(
        text="Arthur Curry kämpfte gegen Black Manta.",
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert result["event_count"] == 1
    assert "participates_in" in edge_types
    assert "occurs_at" not in edge_types
    assert "uses" not in edge_types
