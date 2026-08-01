import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_alias_stops_before_following_verb():
    result = RelationshipIntelligence().analyze(
        text="Arthur Curry alias Aquaman verteidigte Atlantis.",
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert "character_alias:aquaman verteidigte atlantis" not in keys

    assert any(
        edge["edge_type"] == "alias_of"
        and edge["source_node_key"] == "character_alias:aquaman"
        and edge["target_node_key"] == "character:arthur curry"
        for edge in result["edges"]
    )


def test_alias_stops_at_period():
    result = RelationshipIntelligence().analyze(
        text="David Kane ist auch bekannt als Black Manta.",
        source=SOURCE,
    )

    assert any(
        edge["edge_type"] == "alias_of"
        and edge["source_node_key"] == "character_alias:black manta"
        for edge in result["edges"]
    )
