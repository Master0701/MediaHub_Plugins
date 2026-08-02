import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.global_knowledge_fusion import GlobalKnowledgeFusion


def build(**kwargs):
    base = {
        "semantic_result": {},
        "entity_resolution_graph": {},
        "relationship_confidence": {},
        "character_relationship_graph": {},
        "character_timeline": {},
        "character_evolution": {},
        "character_memory": {},
        "franchise_knowledge_graph": {},
        "cross_franchise": {},
        "canonical_conflicts": {},
        "canonical_decisions": {},
        "graph_validation": {},
    }
    base.update(kwargs)
    return GlobalKnowledgeFusion.build(**base)


def test_fuses_and_deduplicates_nodes():
    result = build(
        semantic_result={
            "strategy": "semantic",
            "entity_proposals": [{
                "id": "movie:aquaman-2",
                "title": "Aquaman: Lost Kingdom",
                "entity_type": "movie",
                "confidence": 0.8,
            }],
        },
        franchise_knowledge_graph={
            "strategy": "franchise",
            "nodes": [{
                "id": "movie:aquaman-2",
                "title": "Aquaman: Lost Kingdom",
                "node_type": "movie",
                "confidence": 0.9,
            }],
        },
    )

    assert result["summary"]["node_count"] == 1
    node = result["graph"]["nodes"][0]
    assert node["confidence"] == 0.9
    assert len(node["origins"]) == 2
    assert result["automatic_import"] is False


def test_fuses_relationship_edges():
    result = build(
        character_relationship_graph={
            "strategy": "character_relationship_graph_v600",
            "edges": [{
                "edge_type": "spouse_of",
                "source_node_key": "character:arthur",
                "target_node_key": "character:mera",
                "confidence": 0.8,
            }],
        },
        relationship_confidence={
            "strategy": "relationship_confidence_engine_v620",
            "assessments": [{
                "relation_type": "spouse_of",
                "source_node_key": "character:arthur",
                "target_node_key": "character:mera",
                "confidence": 0.95,
            }],
        },
    )

    assert result["summary"]["edge_count"] == 1
    edge = result["graph"]["edges"][0]
    assert edge["confidence"] == 0.95
    assert len(edge["origins"]) == 2


def test_creates_decision_based_fusion_plan():
    result = build(
        semantic_result={
            "entity_proposals": [{
                "id": "movie:aquaman-2",
                "title": "Aquaman: Lost Kingdom",
                "entity_type": "movie",
            }],
        },
        canonical_decisions={
            "decisions": [{
                "subject_node_key": "movie:aquaman-2",
                "predicate": "year",
                "recommended_value": 2023,
                "confidence": 0.95,
                "decision_type": "prefer_confirmed_consensus",
            }],
        },
    )

    plan = result["fusion_plan"]
    assert len(plan["proposed_updates"]) == 1
    assert plan["applied_update_count"] == 0
    assert plan["automatic_resolution"] is False


def test_no_data_keeps_manual_safety():
    result = build()
    assert result["decision"]["status"] == "no_knowledge_to_fuse"
    assert result["requires_confirmation"] is True
