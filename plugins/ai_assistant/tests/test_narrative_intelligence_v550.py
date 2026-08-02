import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.narrative_intelligence import NarrativeIntelligence


def fused(edge_type, source, target, confidence=0.9):
    return {
        "value": {
            "edge_type": edge_type,
            "source_node_key": source,
            "target_node_key": target,
        },
        "confidence": confidence,
    }


def test_derives_story_arc():
    result = NarrativeIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused(
                    "introduces_conflict",
                    "movie:a",
                    "conflict:black-trident",
                ),
                "b": fused(
                    "resolves_conflict",
                    "movie:a",
                    "event:kordax-defeated",
                ),
            }
        },
        semantic_reasoning={},
        temporal_causal_intelligence={},
    )

    assert result["summary"]["story_arc_count"] == 1
    item = result["conclusions"][0]
    assert item["edge_type"] == "story_arc_from_to"
    assert item["source_node_key"] == "conflict:black-trident"
    assert item["target_node_key"] == "event:kordax-defeated"


def test_derives_character_arc():
    result = NarrativeIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused(
                    "character_growth",
                    "character:orm",
                    "state:cooperates-with-arthur",
                ),
                "b": fused(
                    "changes_allegiance",
                    "character:orm",
                    "state:defends-atlantis",
                ),
            }
        },
        semantic_reasoning={},
        temporal_causal_intelligence={},
    )

    assert result["summary"]["character_arc_count"] == 1
    item = result["conclusions"][0]
    assert item["edge_type"] == "has_character_arc"
    assert len(item["development_steps"]) == 2


def test_detects_narrative_conflict():
    result = NarrativeIntelligence.analyze(
        fusion_result={
            "fused_fields": {
                "a": fused(
                    "character_growth",
                    "character:orm",
                    "state:finale",
                ),
                "b": fused(
                    "character_regression",
                    "character:orm",
                    "state:finale",
                ),
            }
        },
        semantic_reasoning={},
        temporal_causal_intelligence={},
    )

    assert result["summary"]["conflict_count"] == 1
    assert result["decision"]["status"] == "needs_review"
    assert result["automatic_import"] is False
