import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.alias_parser import AliasParser
from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_alias_parser_splits_before_following_verb():
    result = AliasParser.parse(
        "Arthur Curry alias Aquaman verteidigte Atlantis."
    )

    assert result == [
        {
            "primary": "Arthur Curry",
            "alias": "Aquaman",
            "evidence": "Arthur Curry alias Aquaman",
            "separator": "alias",
        }
    ]


def test_alias_parser_supports_auch_bekannt_als():
    result = AliasParser.parse(
        "David Kane ist auch bekannt als Black Manta."
    )

    assert result[0]["primary"] == "David Kane"
    assert result[0]["alias"] == "Black Manta"
    assert result[0]["separator"] == "auch bekannt als"


def test_relationship_intelligence_creates_alias_edge():
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


def test_alias_and_general_rule_work_in_same_text():
    result = RelationshipIntelligence().analyze(
        text=(
            "Arthur Curry alias Aquaman verteidigte Atlantis. "
            "David Kane arbeitet mit Stephen Shin zusammen."
        ),
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "alias_of" in edge_types
    assert "works_with" in edge_types

