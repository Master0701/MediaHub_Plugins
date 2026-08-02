import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cross_franchise_resolver import CrossFranchiseResolver


def build(**kwargs):
    base = {
        "franchise_knowledge_graph": {},
        "entity_resolution_graph": {},
        "canonical_conflicts": {},
        "story_arc_linking": {},
        "semantic_result": {},
    }
    base.update(kwargs)
    return CrossFranchiseResolver.build(**base)


def test_collects_franchise_universe_timeline_nodes():
    result = build(
        franchise_knowledge_graph={
            "strategy": "franchise_knowledge_graph_v590",
            "nodes": [
                {
                    "id": "franchise:dc",
                    "title": "DC",
                    "node_type": "franchise",
                },
                {
                    "id": "universe:dceu",
                    "title": "DCEU",
                    "node_type": "universe",
                },
                {
                    "id": "timeline:dceu-main",
                    "title": "DCEU Main Timeline",
                    "node_type": "timeline",
                },
            ],
        }
    )

    assert result["summary"]["franchise_count"] == 1
    assert result["summary"]["universe_count"] == 1
    assert result["summary"]["timeline_count"] == 1
    assert result["automatic_import"] is False


def test_detects_crossover_and_backdoor_pilot():
    result = build(
        franchise_knowledge_graph={
            "relations": [
                {
                    "relation_type": "crosses_over_with",
                    "source_node_key": "series:arrow",
                    "target_node_key": "series:flash",
                    "confidence": 0.9,
                },
                {
                    "relation_type": "backdoor_pilot_for",
                    "source_node_key": "episode:ncis-220",
                    "target_node_key": "series:ncis-la",
                    "confidence": 0.85,
                },
            ]
        }
    )

    assert result["summary"]["crossover_count"] == 1
    assert result["summary"]["backdoor_pilot_count"] == 1


def test_detects_ambiguous_universe_boundary():
    result = build(
        franchise_knowledge_graph={
            "relations": [
                {
                    "relation_type": "belongs_to_universe",
                    "source_node_key": "movie:example",
                    "target_node_key": "universe:a",
                },
                {
                    "relation_type": "belongs_to_universe",
                    "source_node_key": "movie:example",
                    "target_node_key": "universe:b",
                },
            ]
        }
    )

    assert result["summary"]["ambiguous_boundary_count"] == 1
    assert result["canonical_boundaries"][0]["automatic_resolution"] is False


def test_no_relations_keeps_manual_safety():
    result = build()
    assert (
        result["decision"]["status"]
        == "no_cross_franchise_relations"
    )
    assert result["requires_confirmation"] is True
