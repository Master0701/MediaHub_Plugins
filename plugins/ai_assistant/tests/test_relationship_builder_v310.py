import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.relationship_builder import RelationshipBuilder

SOURCE = {"id": "wiki"}

def test_sequel_target_and_edge():
    result = RelationshipBuilder().build(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "year": 2023,
            "confidence": 0.89,
            "metadata": {},
        },
        text="Der Film ist die Fortsetzung von Aquaman aus dem Jahr 2018.",
        source=SOURCE,
    )
    keys = {n["key"] for n in result["nodes"]}
    types = {e["edge_type"] for e in result["edges"]}
    assert "movie:aquaman:2018" in keys
    assert "sequel_of" in types

def test_cast_relations():
    result = RelationshipBuilder().build(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "year": 2023,
            "confidence": 0.89,
            "metadata": {},
        },
        text="Besetzung Jason Momoa : Arthur Curry / Aquaman Patrick Wilson : Orm Marius Chronologie",
        source=SOURCE,
    )
    node_types = {n["node_type"] for n in result["nodes"]}
    edge_types = {e["edge_type"] for e in result["edges"]}
    assert "person" in node_types
    assert "character" in node_types
    assert "appears_in" in edge_types
    assert "portrayed_by" in edge_types
