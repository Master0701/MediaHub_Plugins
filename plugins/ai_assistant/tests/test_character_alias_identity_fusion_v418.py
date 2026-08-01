import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_alias_identity_fusion import (
    CharacterAliasIdentityFusion,
)


SOURCE = {"id": "wiki"}


def test_aliases_resolve_to_canonical_characters():
    result = CharacterAliasIdentityFusion.build(
        identity_map={
            "arthur": "Arthur Curry",
            "aquaman": "Arthur Curry",
            "david": "David Kane",
            "black manta": "David Kane",
            "orm": "Orm Marius",
        },
        cast_resolution={},
        source=SOURCE,
    )

    assert result["canonical_map"]["arthur"] == "Arthur Curry"
    assert result["canonical_map"]["aquaman"] == "Arthur Curry"
    assert result["canonical_map"]["david"] == "David Kane"
    assert result["canonical_map"]["black manta"] == "David Kane"
    assert result["canonical_map"]["orm"] == "Orm Marius"


def test_transitive_alias_chain_is_flattened():
    result = CharacterAliasIdentityFusion.build(
        identity_map={
            "aquaman": "Arthur",
            "arthur": "Arthur Curry",
        },
        cast_resolution={},
        source=SOURCE,
    )

    assert result["canonical_map"]["aquaman"] == "Arthur Curry"
    assert result["canonical_map"]["arthur"] == "Arthur Curry"


def test_graph_contains_canonical_and_alias_nodes():
    result = CharacterAliasIdentityFusion.build(
        identity_map={
            "arthur": "Arthur Curry",
            "aquaman": "Arthur Curry",
        },
        cast_resolution={},
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }

    assert "character:arthur curry" in keys
    assert "character_alias:arthur" in keys
    assert "character_alias:aquaman" in keys
    assert (
        "alias_of",
        "character_alias:aquaman",
        "character:arthur curry",
    ) in edges


def test_cast_aliases_are_included():
    result = CharacterAliasIdentityFusion.build(
        identity_map={},
        cast_resolution={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "metadata": {
                        "raw_role_name": "Arthur Curry / Aquaman",
                    },
                },
                {
                    "node_type": "character",
                    "title": "Orm Marius",
                    "metadata": {
                        "raw_role_name": "Orm Marius",
                    },
                },
            ]
        },
        source=SOURCE,
    )

    assert result["canonical_map"]["aquaman"] == "Arthur Curry"
    assert result["canonical_map"]["orm"] == "Orm Marius"


def test_results_require_confirmation():
    result = CharacterAliasIdentityFusion.build(
        identity_map={"arthur": "Arthur Curry"},
        cast_resolution={},
        source=SOURCE,
    )

    assert result["strategy"].startswith(
        "character_alias_identity_fusion_v"
    )
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
