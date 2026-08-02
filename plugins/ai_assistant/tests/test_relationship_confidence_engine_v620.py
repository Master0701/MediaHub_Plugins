import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_confidence_engine import (
    RelationshipConfidenceEngine,
)


def build(**kwargs):
    base = {
        "character_relationship_graph": {},
        "franchise_knowledge_graph": {},
        "entity_resolution_graph": {},
        "relationship_intelligence": {},
        "graph_validation": {},
    }
    base.update(kwargs)
    return RelationshipConfidenceEngine.build(**base)


def test_multiple_sources_raise_confidence():
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
        relationship_intelligence={
            "strategy": "wikipedia",
            "conclusions": [{
                "edge_type": "spouse_of",
                "source_node_key": "character:arthur",
                "target_node_key": "character:mera",
                "confidence": 0.9,
            }],
        },
    )

    assessment = result["assessments"][0]
    assert assessment["evidence_count"] == 2
    assert assessment["confidence"] >= 0.75
    assert assessment["automatic_resolution"] is False


def test_conflict_lowers_status():
    result = build(
        character_relationship_graph={
            "strategy": "character_relationship_graph_v600",
            "edges": [{
                "edge_type": "friend_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.8,
            }],
            "conflicts": [{
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "relationship_a": "friend_of",
                "relationship_b": "enemy_of",
            }],
        }
    )

    assessment = result["assessments"][0]
    assert assessment["status"] == "conflicted"
    assert assessment["conflict_count"] == 1


def test_manual_confirmation_can_confirm():
    result = build(
        relationship_intelligence={
            "strategy": "manual_confirmation",
            "conclusions": [{
                "edge_type": "parent_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.95,
                "manual_confirmation": True,
            }],
        }
    )

    assessment = result["assessments"][0]
    assert assessment["status"] == "confirmed"
    assert assessment["manual_confirmation"] is True


def test_confidence_levels():
    assert RelationshipConfidenceEngine.confidence_level(0.95) == "very_high"
    assert RelationshipConfidenceEngine.confidence_level(0.8) == "high"
    assert RelationshipConfidenceEngine.confidence_level(0.6) == "medium"
    assert RelationshipConfidenceEngine.confidence_level(0.4) == "low"
    assert RelationshipConfidenceEngine.confidence_level(0.1) == "very_low"
