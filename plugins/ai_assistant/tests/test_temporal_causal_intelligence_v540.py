import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.temporal_causal_intelligence import TemporalCausalIntelligence


def fused_relation(edge_type, source, target, confidence=0.9):
    return {
        "value": {
            "edge_type": edge_type,
            "source_node_key": source,
            "target_node_key": target,
        },
        "confidence": confidence,
    }


def test_derives_temporal_chain():
    result = TemporalCausalIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused_relation(
                    "happens_before", "event:a", "event:b"
                ),
                "b": fused_relation(
                    "happens_before", "event:b", "event:c"
                ),
            }
        },
        semantic_reasoning={},
    )

    assert result["summary"]["conclusion_count"] == 1
    item = result["conclusions"][0]
    assert item["edge_type"] == "happens_before"
    assert item["source_node_key"] == "event:a"
    assert item["target_node_key"] == "event:c"


def test_derives_causal_chain():
    result = TemporalCausalIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused_relation(
                    "causes", "event:snap", "event:vanishing"
                ),
                "b": fused_relation(
                    "causes", "event:vanishing", "event:endgame"
                ),
            }
        },
        semantic_reasoning={},
    )

    assert result["summary"]["conclusion_count"] == 1
    item = result["conclusions"][0]
    assert item["edge_type"] == "leads_to"
    assert item["source_node_key"] == "event:snap"
    assert item["target_node_key"] == "event:endgame"


def test_detects_temporal_conflict():
    result = TemporalCausalIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused_relation(
                    "happens_before", "event:a", "event:b"
                ),
                "b": fused_relation(
                    "happens_after", "event:a", "event:b"
                ),
            }
        },
        semantic_reasoning={},
    )

    assert result["summary"]["conflict_count"] == 1
    assert result["decision"]["status"] == "needs_review"
    assert result["automatic_import"] is False
