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


def edge_tuples(result):
    return {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }


def test_half_sibling_with_intervening_verb():
    result = analyze(
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis."
    )

    assert (
        "half_sibling_of",
        "character:arthur",
        "character:orm",
    ) in edge_tuples(result)


def test_verb_first_marriage_form():
    result = analyze(
        "Einige Jahre später heiratete Arthur Curry Mera."
    )

    assert (
        "spouse_of",
        "character:arthur curry",
        "character:mera",
    ) in edge_tuples(result)


def test_shared_subject_parent_clause():
    result = analyze(
        "Arthur Curry heiratete Mera und bekam einen Sohn, Arthur Jr."
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


def test_real_aquaman_bundle():
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


def test_strategy_updated():
    result = analyze("Arthur Curry heiratete Mera.")
    assert result["strategy"].startswith("character_relationship_engine_v4")

