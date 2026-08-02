import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.missing_entity_resolver import MissingEntityResolver


def build(orphaned_edges=None, nodes=None):
    return MissingEntityResolver.build(
        knowledge_graph_validation={
            "checks": {
                "edges": {
                    "orphaned_edges": orphaned_edges or []
                }
            }
        },
        global_knowledge={
            "graph": {
                "nodes": nodes or []
            }
        },
    )


def test_creates_missing_entity_proposal():
    result = build(
        orphaned_edges=[{
            "edge_key": (
                "belongs_to_franchise|movie:a|franchise:dc"
            ),
            "missing_nodes": ["franchise:dc"],
        }]
    )

    assert result["summary"]["missing_node_proposal_count"] == 1
    proposal = result["missing_node_proposals"][0]
    assert proposal["node_type"] == "franchise"
    assert proposal["automatic_creation"] is False


def test_deduplicates_repeated_missing_nodes():
    result = build(
        orphaned_edges=[
            {
                "edge_key": "sequel_of|movie:a|movie:b",
                "missing_nodes": ["movie:b"],
            },
            {
                "edge_key": "prequel_of|movie:c|movie:b",
                "missing_nodes": ["movie:b"],
            },
        ]
    )

    assert result["summary"]["missing_node_proposal_count"] == 1
    assert len(
        result["missing_node_proposals"][0]["referenced_by_edges"]
    ) == 2


def test_ignores_nodes_already_present():
    result = build(
        orphaned_edges=[{
            "edge_key": "sequel_of|movie:a|movie:b",
            "missing_nodes": ["movie:b"],
        }],
        nodes=[{
            "node_key": "movie:b",
            "node_type": "movie",
        }],
    )

    assert result["summary"]["missing_node_proposal_count"] == 0
    assert result["decision"]["status"] == "no_missing_entities"


def test_keeps_confirmation_required():
    result = build()
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
