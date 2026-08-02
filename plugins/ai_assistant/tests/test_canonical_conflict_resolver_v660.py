import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.canonical_conflict_resolver import (
    CanonicalConflictResolver,
)


def build(**kwargs):
    base = {
        "entity_resolution_graph": {},
        "relationship_confidence": {},
        "character_timeline": {},
        "character_evolution": {},
        "character_memory": {},
        "graph_validation": {},
    }
    base.update(kwargs)
    return CanonicalConflictResolver.build(**base)


def test_detects_conflicting_values():
    result = build(
        entity_resolution_graph={
            "strategy": "entity_resolution_graph_v610",
            "claims": [
                {
                    "subject_node_key": "character:arthur",
                    "field": "birth_year",
                    "value": 1985,
                    "confidence": 0.8,
                },
                {
                    "subject_node_key": "character:arthur",
                    "field": "birth_year",
                    "value": 1987,
                    "confidence": 0.7,
                },
            ],
        }
    )

    assert result["summary"]["conflict_count"] == 1
    assert result["conflicts"][0]["automatic_resolution"] is False


def test_prefers_manually_confirmed_value():
    result = build(
        entity_resolution_graph={
            "claims": [
                {
                    "subject_node_key": "character:a",
                    "field": "identity",
                    "value": "Aquaman",
                    "confidence": 0.8,
                    "manual_confirmation": True,
                    "source": "manual_confirmation",
                },
                {
                    "subject_node_key": "character:a",
                    "field": "identity",
                    "value": "Ocean Master",
                    "confidence": 0.7,
                },
            ],
        }
    )

    conflict = result["conflicts"][0]
    assert conflict["recommendation"] == "prefer_confirmed_value"
    assert conflict["recommended_value"] == "Aquaman"


def test_close_scores_require_manual_review():
    result = build(
        relationship_confidence={
            "strategy": "relationship_confidence_engine_v620",
            "claims": [
                {
                    "subject_node_key": "character:a",
                    "field": "alignment",
                    "value": "hero",
                    "confidence": 0.7,
                },
                {
                    "subject_node_key": "character:a",
                    "field": "alignment",
                    "value": "antihero",
                    "confidence": 0.69,
                },
            ],
        }
    )

    assert (
        result["conflicts"][0]["recommendation"]
        == "manual_review_required"
    )
    assert result["conflicts"][0]["recommended_value"] is None


def test_no_conflicts_keeps_manual_safety():
    result = build(
        entity_resolution_graph={
            "claims": [{
                "subject_node_key": "character:a",
                "field": "identity",
                "value": "Aquaman",
            }]
        }
    )
    assert result["decision"]["status"] == "no_canonical_conflicts"
    assert result["requires_confirmation"] is True
