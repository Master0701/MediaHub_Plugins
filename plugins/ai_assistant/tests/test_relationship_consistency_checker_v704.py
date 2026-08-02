import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_consistency_checker import (
    RelationshipConsistencyChecker,
)


def build(edges):
    return RelationshipConsistencyChecker.build(
        global_knowledge={"graph": {"edges": edges}},
        knowledge_graph_validation={"status": "pass"},
        missing_entity_resolution={"summary": {}},
    )


def test_valid_inverse_pair_passes():
    result = build([
        {
            "edge_type": "parent_of",
            "source_node_key": "character:a",
            "target_node_key": "character:b",
        },
        {
            "edge_type": "child_of",
            "source_node_key": "character:b",
            "target_node_key": "character:a",
        },
    ])

    assert result["status"] == "pass"


def test_missing_inverse_creates_warning():
    result = build([{
        "edge_type": "parent_of",
        "source_node_key": "character:a",
        "target_node_key": "character:b",
    }])

    assert result["status"] == "warn"
    assert result["summary"]["missing_inverse_count"] == 1


def test_contradictory_relationships_fail():
    result = build([
        {
            "edge_type": "ally_of",
            "source_node_key": "character:a",
            "target_node_key": "character:b",
        },
        {
            "edge_type": "enemy_of",
            "source_node_key": "character:a",
            "target_node_key": "character:b",
        },
    ])

    assert result["status"] == "fail"
    assert result["summary"]["contradiction_count"] == 1


def test_multiple_exclusive_targets_warn():
    result = build([
        {
            "edge_type": "belongs_to_universe",
            "source_node_key": "movie:a",
            "target_node_key": "universe:x",
        },
        {
            "edge_type": "belongs_to_universe",
            "source_node_key": "movie:a",
            "target_node_key": "universe:y",
        },
    ])

    assert result["status"] == "warn"
    assert result["summary"]["exclusive_conflict_count"] == 1
