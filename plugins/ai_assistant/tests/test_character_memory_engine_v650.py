import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_memory_engine import CharacterMemoryEngine


def build(**kwargs):
    base = {
        "character_relationship_graph": {},
        "character_timeline": {},
        "character_evolution": {},
        "relationship_confidence": {},
    }
    base.update(kwargs)
    return CharacterMemoryEngine.build(**base)


def test_builds_relationship_memory():
    result = build(
        character_relationship_graph={
            "strategy": "character_relationship_graph_v600",
            "edges": [{
                "edge_type": "spouse_of",
                "source_node_key": "character:arthur",
                "target_node_key": "character:mera",
                "confidence": 0.8,
            }],
        }
    )

    assert result["summary"]["character_count"] == 1
    assert result["summary"]["memory_count"] == 1
    assert result["profiles"][0]["memories"][0]["memory_type"] == "relationship"
    assert result["automatic_import"] is False


def test_marks_death_as_important_memory():
    result = build(
        character_timeline={
            "strategy": "character_timeline_engine_v630",
            "timelines": [{
                "character_node_key": "character:david-kane",
                "events": [{
                    "event_type": "death",
                    "character_node_key": "character:david-kane",
                    "sequence_index": 5,
                    "confidence": 0.9,
                }],
            }],
        }
    )

    assert result["summary"]["important_memory_count"] == 1
    assert (
        result["profiles"][0]["important_memories"][0]["event_type"]
        == "death"
    )


def test_relationship_confidence_overrides_base_value():
    result = build(
        character_relationship_graph={
            "edges": [{
                "edge_type": "friend_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.4,
            }],
        },
        relationship_confidence={
            "assessments": [{
                "relation_type": "friend_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.9,
            }],
        },
    )

    assert result["profiles"][0]["memories"][0]["confidence"] == 0.9


def test_no_memories_keeps_manual_safety():
    result = build()
    assert result["decision"]["status"] == "no_character_memories"
    assert result["requires_confirmation"] is True
