import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reasoning_intelligence import ReasoningIntelligence


def test_combines_supporting_evidence_and_builds_path():
    result = ReasoningIntelligence.analyze(
        main_node={"key": "movie:aquaman-2"},
        groups={
            "universe": {
                "edges": [{
                    "edge_type": "belongs_to_universe",
                    "source_node_key": "movie:aquaman-2",
                    "target_node_key": "universe:dceu",
                    "confidence": 0.8,
                }]
            },
            "franchise": {
                "observations": [{
                    "relation_type": "belongs_to_universe",
                    "source_node_key": "movie:aquaman-2",
                    "target_node_key": "universe:dceu",
                    "confidence": 0.7,
                }]
            },
        },
    )
    conclusion = result["conclusions"][0]
    assert conclusion["support_count"] == 2
    assert conclusion["confidence"] == 0.94
    assert len(conclusion["evidence_path"]) == 2
    assert result["decision"]["status"] == "supported"
    assert result["automatic_import"] is False


def test_detects_relation_disagreement_for_same_pair():
    result = ReasoningIntelligence.analyze(
        main_node={"key": "movie:test"},
        groups={
            "a": {"edges": [{
                "edge_type": "sequel_of",
                "source_node_key": "movie:b",
                "target_node_key": "movie:a",
                "confidence": 0.9,
            }]},
            "b": {"edges": [{
                "edge_type": "reboot_of",
                "source_node_key": "movie:b",
                "target_node_key": "movie:a",
                "confidence": 0.7,
            }]},
        },
    )
    assert result["summary"]["conflict_count"] == 1
    assert result["decision"]["status"] == "needs_review"
    assert result["conflicts"][0]["automatic_resolution"] is False


def test_graph_validation_warnings_force_review():
    result = ReasoningIntelligence.analyze(
        main_node={"key": "movie:test"},
        groups={},
        graph_validation={
            "summary": {"invalid_count": 0, "warning_count": 2}
        },
    )
    assert result["summary"]["validation_state"] == "review"
    assert result["decision"]["status"] == "needs_review"
