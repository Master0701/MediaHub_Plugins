import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.pipeline_debug_monitor import PipelineDebugMonitor


def test_builds_pipeline_summary():
    snapshot = PipelineDebugMonitor.build(
        modules={
            "reasoning_intelligence": {
                "summary": {
                    "conclusion_count": 4,
                    "conflict_count": 1,
                },
                "decision": {"status": "needs_review"},
            },
            "multi_source_fusion": {
                "summary": {
                    "field_count": 8,
                    "evidence_count": 12,
                    "duplicate_count": 2,
                    "conflict_count": 1,
                },
                "decision": {"status": "needs_review"},
            },
            "graph_validation": {
                "summary": {
                    "invalid_count": 0,
                    "warning_count": 2,
                }
            },
        },
        source={"id": "source-1"},
    )

    assert snapshot["status"] == "review"
    assert snapshot["summary"]["fusion_field_count"] == 8
    assert snapshot["summary"]["fusion_evidence_count"] == 12
    assert snapshot["summary"]["reasoning_conclusion_count"] == 4
    assert snapshot["summary"]["graph_warning_count"] == 2
    assert snapshot["automatic_import"] is False


def test_relationship_fields_remain_visible_in_fusion_summary():
    snapshot = PipelineDebugMonitor.build(
        modules={
            "multi_source_fusion": {
                "summary": {
                    "field_count": 30,
                    "evidence_count": 30,
                    "duplicate_count": 0,
                    "conflict_count": 0,
                },
                "fused_fields": {
                    "supported_relationship:sequel_of:a:b": {},
                    "supported_relationship:belongs_to_universe:a:c": {},
                },
            }
        }
    )

    assert snapshot["summary"]["fusion_field_count"] == 30
    assert snapshot["summary"]["fusion_duplicate_count"] == 0


def test_formats_readable_text():
    snapshot = PipelineDebugMonitor.build(
        modules={
            "multi_source_fusion": {
                "summary": {
                    "field_count": 3,
                    "evidence_count": 5,
                }
            }
        }
    )

    text = PipelineDebugMonitor.format_text(snapshot)

    assert "KI-PIPELINE-DEBUG" in text
    assert "Fusion-Felder: 3" in text
    assert "multi_source_fusion" in text

