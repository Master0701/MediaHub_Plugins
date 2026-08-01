import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_graph_builder import KnowledgeGraphBuilder


def test_direct_knowledge_result_nodes_and_edges():
    result = KnowledgeGraphBuilder.build(
        source={"id": "wiki"},
        knowledge_result={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                    "confidence": 0.9,
                },
                {
                    "node_type": "location",
                    "title": "Atlantis",
                    "key": "location:atlantis",
                    "confidence": 0.8,
                },
            ],
            "edges": [
                {
                    "edge_type": "rules",
                    "source_node_key": "character:arthur curry",
                    "target_node_key": "location:atlantis",
                    "confidence": 0.85,
                }
            ],
        },
    )

    keys = {item["key"] for item in result["nodes"]}
    edge_types = {item["edge_type"] for item in result["edges"]}

    assert "character:arthur curry" in keys
    assert "location:atlantis" in keys
    assert "rules" in edge_types


def test_graph_proposal_is_supported():
    result = KnowledgeGraphBuilder.build(
        source={"id": "wiki"},
        knowledge_result={
            "graph_proposal": {
                "nodes": [
                    {
                        "node_type": "movie",
                        "title": "Aquaman",
                        "key": "movie:aquaman",
                    }
                ],
                "edges": [],
            }
        },
    )

    assert result["statistics"]["node_count"] == 1
    assert result["nodes"][0]["key"] == "movie:aquaman"


def test_entity_and_relation_proposals_are_supported():
    result = KnowledgeGraphBuilder.build(
        source={"id": "wiki"},
        knowledge_result={
            "entity_proposals": [
                {
                    "entity_type": "movie",
                    "title": "Aquaman",
                    "confidence": 0.88,
                }
            ],
            "relation_proposals": [
                {
                    "relation_type": "belongs_to",
                    "source_key": "movie:aquaman",
                    "target_key": "universe:dc extended universe",
                    "confidence": 0.75,
                }
            ],
        },
    )

    keys = {item["key"] for item in result["nodes"]}

    assert "movie:aquaman" in keys
    assert "universe:dc extended universe" in keys
    assert result["statistics"]["edge_count"] == 1


def test_old_and_new_inputs_can_be_combined():
    result = KnowledgeGraphBuilder.build(
        source={"id": "wiki"},
        parser_result={
            "result": {
                "fields": {
                    "title": "Aquaman: Lost Kingdom",
                    "media_type": "movie",
                }
            }
        },
        semantic_result={
            "primary_entity_type": "movie",
            "primary_entity_confidence": 0.84,
        },
        classified_fields={
            "primary_values": {
                "release_year": 2023,
            }
        },
        scan_result={"text_preview": ""},
        knowledge_result={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                }
            ]
        },
        node_groups=[
            [
                {
                    "node_type": "location",
                    "title": "Atlantis",
                    "key": "location:atlantis",
                }
            ]
        ],
    )

    keys = {item["key"] for item in result["nodes"]}

    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "character:arthur curry" in keys
    assert "location:atlantis" in keys
    assert result["strategy"] == "knowledge_graph_builder_v402"
