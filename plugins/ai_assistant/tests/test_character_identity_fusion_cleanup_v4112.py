import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_alias_identity_fusion import CharacterAliasIdentityFusion


SOURCE = {"id": "wiki"}


def cast_data():
    return {
        "nodes": [
            {"key": "person:jason momoa", "node_type": "person", "title": "Jason Momoa", "metadata": {}},
            {"key": "person:amber heard", "node_type": "person", "title": "Amber Heard", "metadata": {}},
            {"key": "character:arthur curry", "node_type": "character", "title": "Arthur Curry", "metadata": {"raw_role_name": "Arthur Curry / Aquaman"}},
            {"key": "character:david kane", "node_type": "character", "title": "David Kane", "metadata": {"raw_role_name": "David Kane / Black Manta"}},
            {"key": "character:königin atlanna", "node_type": "character", "title": "Königin Atlanna", "metadata": {"raw_role_name": "Königin Atlanna"}},
            {"key": "character:dr. stephen shin", "node_type": "character", "title": "Dr. Stephen Shin", "metadata": {"raw_role_name": "Dr. Stephen Shin"}},
        ],
        "edges": [
            {
                "edge_type": "alias_of",
                "source_node_key": "character_alias:black manta",
                "target_node_key": "character:david kane",
            }
        ],
    }


def test_real_people_are_not_character_identities():
    result = CharacterAliasIdentityFusion.build(
        identity_map={
            "jason": "Jason Momoa",
            "amber": "Amber Heard",
            "arthur": "Arthur Curry",
        },
        cast_resolution=cast_data(),
        source=SOURCE,
    )
    titles = {
        node["title"]
        for node in result["nodes"]
        if node["node_type"] == "character"
    }
    assert "Jason Momoa" not in titles
    assert "Amber Heard" not in titles
    assert "Arthur Curry" in titles


def test_honorifics_are_not_aliases():
    result = CharacterAliasIdentityFusion.build(
        identity_map={},
        cast_resolution=cast_data(),
        source=SOURCE,
    )
    assert "königin" not in result["canonical_map"]
    assert "dr." not in result["canonical_map"]


def test_canonical_case_is_preserved():
    result = CharacterAliasIdentityFusion.build(
        identity_map={},
        cast_resolution=cast_data(),
        source=SOURCE,
    )
    assert result["canonical_map"]["black manta"] == "David Kane"


def test_real_character_aliases_remain():
    result = CharacterAliasIdentityFusion.build(
        identity_map={"arthur": "Arthur Curry"},
        cast_resolution=cast_data(),
        source=SOURCE,
    )
    assert result["canonical_map"]["arthur"] == "Arthur Curry"
    assert result["canonical_map"]["aquaman"] == "Arthur Curry"
    assert result["canonical_map"]["black manta"] == "David Kane"


def test_strategy_v4112():
    result = CharacterAliasIdentityFusion.build(
        identity_map={},
        cast_resolution=cast_data(),
        source=SOURCE,
    )
    assert result["strategy"] == "character_alias_identity_fusion_v4112"
