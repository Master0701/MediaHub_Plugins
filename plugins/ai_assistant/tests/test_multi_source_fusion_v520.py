import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.multi_source_fusion import MultiSourceFusion


def test_fuses_matching_values_from_multiple_sources():
    result = MultiSourceFusion.fuse(
        sources={
            "tmdb": {
                "title": "Aquaman and the Lost Kingdom",
                "year": 2023,
                "confidence": 0.8,
            },
            "wikipedia": {
                "title": "Aquaman and the Lost Kingdom",
                "year": 2023,
                "confidence": 0.7,
            },
        }
    )

    title = result["fused_fields"]["title"]
    assert title["value"] == "Aquaman and the Lost Kingdom"
    assert title["support_count"] == 2
    assert title["confidence"] > 0.8
    assert result["summary"]["duplicate_count"] >= 2
    assert result["decision"]["status"] == "fused"


def test_marks_conflicting_values_without_auto_resolution():
    result = MultiSourceFusion.fuse(
        sources={
            "tmdb": {
                "media_type": "movie",
                "confidence": 0.9,
            },
            "ocr": {
                "media_type": "series",
                "confidence": 0.8,
            },
        }
    )

    assert result["summary"]["conflict_count"] == 1
    assert result["decision"]["status"] == "needs_review"
    assert result["conflicts"][0]["automatic_resolution"] is False
    assert result["automatic_import"] is False


def test_user_confirmation_receives_highest_default_weight():
    result = MultiSourceFusion.fuse(
        sources={
            "user_confirmation": {
                "title": "Correct Title",
                "confidence": 1.0,
            },
            "ocr": {
                "title": "Wrong Title",
                "confidence": 1.0,
            },
        }
    )

    assert result["fused_fields"]["title"]["value"] == "Correct Title"


def test_keeps_distinct_reasoning_relationships_separate():
    result = MultiSourceFusion.fuse(
        sources={
            "reasoning_intelligence": {
                "conclusions": [
                    {
                        "conclusion_type": "supported_relationship",
                        "edge_type": "sequel_of",
                        "source_node_key": "movie:aquaman-2",
                        "target_node_key": "movie:aquaman",
                        "confidence": 0.9,
                    },
                    {
                        "conclusion_type": "supported_relationship",
                        "edge_type": "belongs_to_universe",
                        "source_node_key": "movie:aquaman-2",
                        "target_node_key": "universe:dceu",
                        "confidence": 0.8,
                    },
                    {
                        "conclusion_type": "supported_relationship",
                        "edge_type": "installment_of",
                        "source_node_key": "movie:aquaman-2",
                        "target_node_key": "franchise:aquaman",
                        "confidence": 0.85,
                    },
                ]
            }
        }
    )

    relationship_fields = [
        key
        for key in result["fused_fields"]
        if key.startswith("supported_relationship:")
    ]

    assert len(relationship_fields) == 3
    assert result["summary"]["conflict_count"] == 0
    assert result["summary"]["duplicate_count"] == 0

    for field in relationship_fields:
        item = result["fused_fields"][field]
        assert item["support_count"] == 1
        assert item["evidence_path"][0]["value_key"]


def test_fuses_only_the_same_relationship_from_multiple_sources():
    relationship = {
        "conclusion_type": "supported_relationship",
        "edge_type": "sequel_of",
        "source_node_key": "movie:aquaman-2",
        "target_node_key": "movie:aquaman",
    }

    result = MultiSourceFusion.fuse(
        sources={
            "reasoning_intelligence": {
                "conclusions": [
                    {**relationship, "confidence": 0.8}
                ]
            },
            "knowledge_graph": {
                "conclusions": [
                    {**relationship, "confidence": 0.7}
                ]
            },
        }
    )

    relationship_fields = [
        key
        for key in result["fused_fields"]
        if key.startswith("supported_relationship:")
    ]

    assert len(relationship_fields) == 1
    fused = result["fused_fields"][relationship_fields[0]]
    assert fused["support_count"] == 2
    assert fused["confidence"] > 0.8
    assert result["summary"]["duplicate_count"] == 1
    assert result["summary"]["conflict_count"] == 0

