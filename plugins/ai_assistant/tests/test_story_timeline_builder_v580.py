import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.story_timeline_builder import StoryTimelineBuilder


def relation(edge, owner, target, sentence, confidence=0.7):
    return {
        "edge_type": edge,
        "source_node_key": owner,
        "target_node_key": target,
        "sentence": sentence,
        "confidence": confidence,
    }


def test_builds_ordered_timeline():
    result = StoryTimelineBuilder.build(
        narrative_extraction={
            "relations": [
                relation(
                    "introduces_conflict",
                    "media:a",
                    "conflict:2:attack",
                    "David greift Atlantis an.",
                ),
                relation(
                    "resolves_conflict",
                    "media:a",
                    "resolution:8:victory",
                    "Danach besiegt Arthur Kordax.",
                ),
            ]
        },
        story_arc_linking={"arcs": []},
    )

    assert result["summary"]["event_count"] == 2
    assert result["summary"]["link_count"] == 1
    assert result["links"][0]["relation_type"] == "before"
    assert result["automatic_import"] is False


def test_detects_parallel_marker():
    result = StoryTimelineBuilder.build(
        narrative_extraction={
            "relations": [
                relation(
                    "introduces_conflict",
                    "media:a",
                    "conflict:1:first",
                    "Arthur kämpft in Necrus.",
                ),
                relation(
                    "character_growth",
                    "character:orm",
                    "development:2:parallel",
                    "Währenddessen hilft Orm Mera.",
                ),
            ]
        },
        story_arc_linking={"arcs": []},
    )

    assert result["summary"]["parallel_link_count"] == 1


def test_includes_story_arc_windows():
    result = StoryTimelineBuilder.build(
        narrative_extraction={"relations": []},
        story_arc_linking={
            "arcs": [
                {
                    "arc_type": "conflict_resolution_arc",
                    "owner_node_key": "media:a",
                    "start_node_key": "conflict:1:a",
                    "end_node_key": "resolution:9:b",
                    "confidence": 0.6,
                }
            ]
        },
    )

    assert result["summary"]["arc_window_count"] == 1
