import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_timeline_engine import CharacterTimelineEngine


def build(**kwargs):
    base = {
        "character_relationship_graph": {},
        "story_timeline": {},
        "relationship_confidence": {},
        "narrative_intelligence": {},
        "event_intelligence": {},
    }
    base.update(kwargs)
    return CharacterTimelineEngine.build(**base)


def test_builds_character_timeline():
    result = build(
        event_intelligence={
            "strategy": "event_intelligence",
            "events": [
                {
                    "event_type": "coronation",
                    "character_node_key": "character:arthur",
                    "sequence_index": 1,
                    "confidence": 0.8,
                },
                {
                    "event_type": "marriage",
                    "character_node_key": "character:arthur",
                    "sequence_index": 2,
                    "confidence": 0.9,
                },
            ],
        }
    )

    assert result["summary"]["character_count"] == 1
    assert result["summary"]["event_count"] == 2
    assert result["timelines"][0]["link_count"] == 1
    assert result["automatic_import"] is False


def test_detects_temporal_parallel_link():
    result = build(
        event_intelligence={
            "events": [
                {
                    "event_type": "battle",
                    "character_node_key": "character:arthur",
                    "sequence_index": 1,
                    "sentence": "Arthur kämpft in Necrus.",
                },
                {
                    "event_type": "rescue",
                    "character_node_key": "character:arthur",
                    "sequence_index": 2,
                    "sentence": "Währenddessen rettet Mera Arthur Jr.",
                },
            ],
        }
    )

    assert (
        result["timelines"][0]["links"][0]["relation_type"]
        == "parallel_to"
    )


def test_infers_event_type_from_sentence():
    result = build(
        narrative_intelligence={
            "relations": [
                {
                    "source_node_key": "character:arthur",
                    "sentence": "Arthur wurde zum König gekrönt.",
                    "confidence": 0.7,
                }
            ]
        }
    )

    assert (
        result["timelines"][0]["events"][0]["event_type"]
        == "coronation"
    )


def test_no_events_keeps_manual_safety():
    result = build()
    assert result["decision"]["status"] == "no_character_events"
    assert result["requires_confirmation"] is True
