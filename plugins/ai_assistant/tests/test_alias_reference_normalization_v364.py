import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.alias_parser import AliasParser
from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_alias_sentence_does_not_create_combined_character():
    result = RelationshipIntelligence().analyze(
        text="Arthur Curry alias Aquaman verteidigte Atlantis.",
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert "character:arthur curry alias aquaman" not in keys

    assert any(
        edge["edge_type"] == "alias_of"
        and edge["source_node_key"] == "character_alias:aquaman"
        and edge["target_node_key"] == "character:arthur curry"
        for edge in result["edges"]
    )


def test_general_relation_uses_primary_character():
    result = RelationshipIntelligence().analyze(
        text="Arthur Curry alias Aquaman verteidigte Atlantis.",
        source=SOURCE,
    )

    assert any(
        edge["edge_type"] == "protects"
        and edge["source_node_key"] == "character:arthur curry"
        for edge in result["edges"]
    )


def test_auch_bekannt_als_removes_copula():
    parsed = AliasParser.parse(
        "David Kane ist auch bekannt als Black Manta."
    )

    assert parsed[0]["primary"] == "David Kane"
    assert parsed[0]["alias"] == "Black Manta"
