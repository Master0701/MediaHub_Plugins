import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_graph_validator import KnowledgeGraphValidator


def build(nodes=None, edges=None):
    return KnowledgeGraphValidator.build(
        global_knowledge={
            "graph": {
                "nodes": nodes or [],
                "edges": edges or [],
            }
        }
    )


def test_valid_graph_passes():
    result = build(
        nodes=[
            {
                "node_key": "movie:a",
                "node_type": "movie",
            },
            {
                "node_key": "franchise:x",
                "node_type": "franchise",
            },
        ],
        edges=[{
            "edge_type": "belongs_to_franchise",
            "source_node_key": "movie:a",
            "target_node_key": "franchise:x",
        }],
    )
    assert result["status"] == "pass"


def test_detects_orphaned_edge():
    result = build(
        nodes=[{
            "node_key": "movie:a",
            "node_type": "movie",
        }],
        edges=[{
            "edge_type": "sequel_of",
            "source_node_key": "movie:a",
            "target_node_key": "movie:missing",
        }],
    )
    assert result["status"] == "fail"
    assert result["summary"]["orphaned_edge_count"] == 1


def test_detects_duplicate_nodes_and_edges():
    node = {
        "node_key": "movie:a",
        "node_type": "movie",
    }
    edge = {
        "edge_type": "sequel_of",
        "source_node_key": "movie:a",
        "target_node_key": "movie:b",
    }
    result = build(
        nodes=[
            node,
            dict(node),
            {
                "node_key": "movie:b",
                "node_type": "movie",
            },
        ],
        edges=[edge, dict(edge)],
    )
    assert result["status"] == "fail"
    assert result["summary"]["duplicate_node_count"] == 1
    assert result["summary"]["duplicate_edge_count"] == 1


def test_detects_cycle_in_dag_relation():
    result = build(
        nodes=[
            {
                "node_key": "movie:a",
                "node_type": "movie",
            },
            {
                "node_key": "movie:b",
                "node_type": "movie",
            },
        ],
        edges=[
            {
                "edge_type": "sequel_of",
                "source_node_key": "movie:a",
                "target_node_key": "movie:b",
            },
            {
                "edge_type": "sequel_of",
                "source_node_key": "movie:b",
                "target_node_key": "movie:a",
            },
        ],
    )
    assert result["status"] == "fail"
    assert result["summary"]["cycle_count"] >= 1
