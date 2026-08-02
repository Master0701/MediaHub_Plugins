import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.entity_resolution_graph import EntityResolutionGraph


def build(**kwargs):
    base = {
        "semantic_result": {},
        "franchise_knowledge_graph": {},
        "character_relationship_graph": {},
        "character_identity_fusion": {},
        "relationship_identity_map": {},
    }
    base.update(kwargs)
    return EntityResolutionGraph.build(**base)


def test_detects_exact_title_duplicate():
    result = build(
        franchise_knowledge_graph={
            "strategy": "franchise_knowledge_graph_v590",
            "nodes": [
                {
                    "id": "media:aquaman-1",
                    "title": "Aquaman",
                    "node_type": "movie",
                    "year": 2018,
                },
                {
                    "id": "media:aquaman-copy",
                    "title": "AQUAMAN",
                    "node_type": "movie",
                    "year": 2018,
                },
            ],
        }
    )

    assert result["summary"]["merge_candidate_count"] == 1
    assert result["merge_proposals"][0]["automatic_resolution"] is False


def test_detects_alias_identity_candidate():
    result = build(
        character_relationship_graph={
            "strategy": "character_relationship_graph_v600",
            "edges": [
                {
                    "edge_type": "alias_of",
                    "source_node_key": "character:arthur-curry",
                    "target_node_key": "identity:aquaman",
                    "confidence": 0.9,
                }
            ],
        }
    )

    assert result["summary"]["identity_link_candidate_count"] == 1
    assert result["requires_confirmation"] is True


def test_reports_same_name_type_conflict():
    result = build(
        franchise_knowledge_graph={
            "nodes": [
                {
                    "id": "movie:flash",
                    "title": "The Flash",
                    "node_type": "movie",
                },
                {
                    "id": "series:flash",
                    "title": "The Flash",
                    "node_type": "series",
                },
            ],
        }
    )

    assert result["summary"]["conflict_count"] == 1
