import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_intelligence import CharacterIntelligence


SOURCE = {"id": "wiki"}


def test_marriage_and_parent_child_relations():
    text = (
        "Arthur Curry heiratete Mera und bekam einen Sohn, Arthur Jr."
    )
    result = CharacterIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "married_to" in edge_types
    assert "parent_of" in edge_types
    assert "child_of" in edge_types


def test_ruler_and_location_relations():
    text = "Arthur Curry wurde König von Atlantis."
    result = CharacterIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "character:arthur curry" in keys
    assert "location:atlantis" in keys
    assert "ruler_of" in edge_types
    assert "lives_in" in edge_types


def test_sibling_relation_is_symmetric():
    text = "Orm ist der Halbbruder von Arthur Curry."
    result = CharacterIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    sibling_edges = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "sibling_of"
    ]

    assert len(sibling_edges) == 2
