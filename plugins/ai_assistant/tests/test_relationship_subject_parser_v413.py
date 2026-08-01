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


def edges(result):
    return {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }


def test_normal_main_clause_subject():
    result = analyze(
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis."
    )

    assert (
        "half_sibling_of",
        "character:arthur",
        "character:orm",
    ) in edges(result)


def test_subject_after_introductory_clause():
    result = analyze(
        "Um herauszufinden, wo David sich versteckt, "
        "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis."
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:um" not in keys
    assert "character:arthur" in keys
    assert "character:orm" in keys


def test_subject_after_introductory_clause_uses_identities():
    result = analyze(
        "Um herauszufinden, wo David sich versteckt, "
        "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis.",
        IDENTITIES,
    )

    relation_edges = edges(result)

    assert (
        "half_sibling_of",
        "character:arthur curry",
        "character:orm marius",
    ) in relation_edges
    assert (
        "half_sibling_of",
        "character:orm marius",
        "character:arthur curry",
    ) in relation_edges


def test_existing_family_bundle_remains_intact():
    result = analyze(
        "Arthur Curry heiratete Mera und bekam einen Sohn, Arthur Jr. "
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis. "
        "Kordax, dem Bruder von König Atlan und Herrscher von Necrus."
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert {
        "spouse_of",
        "parent_of",
        "child_of",
        "half_sibling_of",
        "sibling_of",
    } <= edge_types


def test_strategy_v413():
    result = analyze("Arthur Curry heiratete Mera.")
    assert result["strategy"] == "character_relationship_engine_v413"
