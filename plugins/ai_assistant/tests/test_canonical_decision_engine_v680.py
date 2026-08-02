import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.canonical_decision_engine import (
    CanonicalDecisionEngine,
)


def build(**kwargs):
    base = {
        "canonical_conflicts": {},
        "relationship_confidence": {},
        "cross_franchise": {},
        "graph_validation": {},
        "entity_resolution_graph": {},
    }
    base.update(kwargs)
    return CanonicalDecisionEngine.build(**base)


def test_prefers_confirmed_consensus():
    result = build(
        canonical_conflicts={
            "strategy": "canonical_conflict_resolver_v660",
            "conflicts": [{
                "subject_node_key": "movie:aquaman-2",
                "predicate": "year",
                "candidates": [
                    {
                        "value": 2023,
                        "score": 0.92,
                        "source_count": 3,
                        "sources": ["wikidata", "tmdb", "wikipedia"],
                    },
                    {
                        "value": 2022,
                        "score": 0.75,
                        "source_count": 1,
                        "sources": ["unknown"],
                    },
                ],
            }],
        }
    )

    decision = result["decisions"][0]
    assert decision["decision_type"] == "prefer_confirmed_consensus"
    assert decision["recommended_value"] == 2023
    assert decision["automatic_resolution"] is False


def test_manual_confirmation_wins():
    result = build(
        canonical_conflicts={
            "conflicts": [{
                "subject_node_key": "character:arthur",
                "predicate": "identity",
                "candidates": [
                    {
                        "value": "Aquaman",
                        "score": 0.9,
                        "source_count": 1,
                        "sources": ["manual_confirmation"],
                        "manual_confirmation": True,
                    },
                    {
                        "value": "Ocean Master",
                        "score": 0.8,
                        "source_count": 2,
                        "sources": ["wikipedia", "tmdb"],
                    },
                ],
            }],
        }
    )

    assert (
        result["decisions"][0]["decision_type"]
        == "prefer_confirmed_value"
    )
    assert (
        result["decisions"][0]["recommended_value"]
        == "Aquaman"
    )


def test_boundary_conflict_can_force_manual_review():
    result = build(
        relationship_confidence={
            "assessments": [{
                "relation_type": "belongs_to_universe",
                "source_node_key": "movie:example",
                "target_node_key": "universe:a",
                "confidence": 0.75,
                "independent_source_count": 1,
            }],
        },
        cross_franchise={
            "canonical_boundaries": [{
                "node_key": "movie:example",
                "status": "ambiguous_boundary",
            }],
        },
    )

    decision = result["decisions"][0]
    assert decision["decision_type"] == "manual_review_required"
    assert decision["recommended_value"] is None


def test_no_candidates_keeps_manual_safety():
    result = build()
    assert result["decision"]["status"] == "no_canonical_decisions"
    assert result["requires_confirmation"] is True
