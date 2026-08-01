import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_relationship_engine import CharacterRelationshipEngine


SOURCE = {"id": "wiki"}


def analyze(text):
    return CharacterRelationshipEngine.analyze(
        text=text,
        source=SOURCE,
    )


def test_spouse_relationship():
    result = analyze("Arthur Curry heiratete Mera.")

    edge_types = {edge["edge_type"] for edge in result["edges"]}
    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "character:mera" in keys
    assert edge_types == {"spouse_of"}
    assert result["relationship_count"] == 2


def test_parent_child_relationship():
    result = analyze(
        "Arthur Curry bekam einen Sohn, Arthur Jr."
    )

    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }

    assert (
        "parent_of",
        "character:arthur curry",
        "character:arthur jr",
    ) in edges
    assert (
        "child_of",
        "character:arthur jr",
        "character:arthur curry",
    ) in edges


def test_half_sibling_relationship():
    result = analyze(
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis."
    )

    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }

    assert (
        "half_sibling_of",
        "character:arthur",
        "character:orm",
    ) in edges
    assert (
        "half_sibling_of",
        "character:orm",
        "character:arthur",
    ) in edges


def test_explicit_brother_relationship():
    result = analyze(
        "Kordax, dem Bruder von König Atlan und Herrscher von Necrus."
    )

    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }

    assert (
        "sibling_of",
        "character:kordax",
        "character:könig atlan",
    ) in edges


def test_real_aquaman_relationship_bundle():
    result = analyze(
        "Einige Jahre nachdem er König von Atlantis geworden war, "
        "heiratete Arthur Curry Mera und bekam einen Sohn, Arthur Jr. "
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
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
