import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_relationship_engine import CharacterRelationshipEngine


SOURCE = {"id": "wiki"}
IDENTITIES = {
    "arthur": "Arthur Curry",
    "orm": "Orm Marius",
}


def analyze(text, identities=None):
    return CharacterRelationshipEngine.analyze(
        text=text,
        source=SOURCE,
        identity_map=identities or {},
    )


def edge_tuples(result):
    return {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }


def test_leading_um_clause_is_not_character():
    result = analyze(
        "Um herauszufinden, wo David sich versteckt, "
        "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis."
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:um" not in keys
    assert "character:arthur" in keys
    assert "character:orm" in keys


def test_half_siblings_use_canonical_identity_map():
    result = analyze(
        "Um herauszufinden, wo David sich versteckt, "
        "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis.",
        IDENTITIES,
    )

    edges = edge_tuples(result)

    assert (
        "half_sibling_of",
        "character:arthur curry",
        "character:orm marius",
    ) in edges
    assert (
        "half_sibling_of",
        "character:orm marius",
        "character:arthur curry",
    ) in edges


def test_marriage_and_child_identity_resolution():
    result = analyze(
        "Arthur heiratete Mera und bekam einen Sohn, Arthur Jr.",
        IDENTITIES,
    )

    edges = edge_tuples(result)

    assert (
        "spouse_of",
        "character:arthur curry",
        "character:mera",
    ) in edges
    assert (
        "parent_of",
        "character:arthur curry",
        "character:arthur jr",
    ) in edges


def test_strategy_v412():
    result = analyze("Arthur heiratete Mera.", IDENTITIES)
    assert result["strategy"].startswith("character_relationship_engine_v4")

