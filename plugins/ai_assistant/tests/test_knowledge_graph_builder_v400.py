import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_graph_builder import KnowledgeGraphBuilder


SOURCE = {"id": "wiki"}


def test_duplicate_nodes_are_merged():
    result = KnowledgeGraphBuilder.build(
        node_groups=[
            [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                    "confidence": 0.80,
                    "metadata": {"alias": "Aquaman"},
                }
            ],
            [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                    "confidence": 0.92,
                    "metadata": {"kingdom": "Atlantis"},
                }
            ],
        ],
        source=SOURCE,
    )

    assert result["statistics"]["node_count"] == 1
    node = result["nodes"][0]
    assert node["confidence"] == 0.92
    assert node["metadata"]["alias"] == "Aquaman"
    assert node["metadata"]["kingdom"] == "Atlantis"


def test_duplicate_edges_are_merged():
    result = KnowledgeGraphBuilder.build(
        node_groups=[
            [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                },
                {
                    "node_type": "character",
                    "title": "David Kane",
                    "key": "character:david kane",
                },
            ]
        ],
        edge_groups=[
            [
                {
                    "edge_type": "fights",
                    "source_node_key": "character:arthur curry",
                    "target_node_key": "character:david kane",
                    "confidence": 0.70,
                }
            ],
            [
                {
                    "edge_type": "fights",
                    "source_node_key": "character:arthur curry",
                    "target_node_key": "character:david kane",
                    "confidence": 0.90,
                }
            ],
        ],
        source=SOURCE,
    )

    assert result["statistics"]["edge_count"] == 1
    assert result["edges"][0]["confidence"] == 0.90


def test_missing_edge_endpoint_creates_placeholder():
    result = KnowledgeGraphBuilder.build(
        edge_groups=[
            [
                {
                    "edge_type": "located_in",
                    "source_node_key": "character:arthur curry",
                    "target_node_key": "location:atlantis",
                    "confidence": 0.75,
                }
            ]
        ],
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur curry" in keys
    assert "location:atlantis" in keys
    assert result["statistics"]["placeholder_node_count"] == 2


def test_statistics_are_generated():
    result = KnowledgeGraphBuilder.build(
        node_groups=[
            [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                },
                {
                    "node_type": "location",
                    "title": "Atlantis",
                },
            ]
        ],
        edge_groups=[
            [
                {
                    "edge_type": "rules",
                    "source_node_key": "character:arthur curry",
                    "target_node_key": "location:atlantis",
                }
            ]
        ],
        source=SOURCE,
    )

    assert result["statistics"]["node_types"] == {
        "character": 1,
        "location": 1,
    }
    assert result["statistics"]["edge_types"] == {
        "rules": 1,
    }
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
