import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.story_arc_linker import StoryArcLinker


def item(edge, owner, target, confidence=0.7):
    return {
        "edge_type": edge,
        "source_node_key": owner,
        "target_node_key": target,
        "confidence": confidence,
    }


def test_conflict_resolution_link():
    result = StoryArcLinker.link(
        narrative_extraction={
            "relations": [
                item("introduces_conflict", "media:a", "conflict:2:x"),
                item("resolves_conflict", "media:a", "resolution:7:y"),
            ]
        },
        narrative_intelligence={},
    )
    assert result["summary"]["conflict_resolution_arc_count"] == 1
    assert result["automatic_import"] is False


def test_character_development_link():
    result = StoryArcLinker.link(
        narrative_extraction={
            "relations": [
                item("character_growth", "character:orm", "development:3:a"),
                item("character_growth", "character:orm", "development:8:b"),
            ]
        },
        narrative_intelligence={},
    )
    assert result["summary"]["character_development_arc_count"] == 1


def test_multi_arc_chain():
    result = StoryArcLinker.link(
        narrative_extraction={"relations": []},
        narrative_intelligence={
            "conclusions": [
                {
                    "conclusion_type": "story_arc",
                    "arc_owner_node_key": "media:a",
                    "source_node_key": "conflict:1:a",
                    "target_node_key": "resolution:2:a",
                    "confidence": 0.7,
                },
                {
                    "conclusion_type": "story_arc",
                    "arc_owner_node_key": "media:a",
                    "source_node_key": "conflict:3:b",
                    "target_node_key": "resolution:4:b",
                    "confidence": 0.68,
                },
            ]
        },
    )
    assert result["summary"]["linked_story_arc_chain_count"] == 1
