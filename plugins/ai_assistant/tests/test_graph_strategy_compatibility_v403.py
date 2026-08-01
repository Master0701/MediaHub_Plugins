import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_graph_builder import KnowledgeGraphBuilder


def test_current_strategy_for_new_group_api():
    result = KnowledgeGraphBuilder.build(
        node_groups=[[
            {
                "node_type": "character",
                "title": "Arthur Curry",
                "key": "character:arthur curry",
            }
        ]],
        source={"id": "wiki"},
    )

    assert result["strategy"] == "knowledge_graph_builder_v402"


def test_current_strategy_for_knowledge_result_api():
    result = KnowledgeGraphBuilder.build(
        knowledge_result={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "key": "character:arthur curry",
                }
            ]
        },
        source={"id": "wiki"},
    )

    assert result["strategy"] == "knowledge_graph_builder_v402"


def test_legacy_and_knowledge_result_inputs_combine():
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
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "character:arthur curry" in keys
    assert result["strategy"] == "knowledge_graph_builder_v402"
