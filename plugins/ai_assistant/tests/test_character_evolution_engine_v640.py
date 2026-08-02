import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_evolution_engine import CharacterEvolutionEngine


def build(**kwargs):
    base = {
        "character_timeline": {},
        "character_relationship_graph": {},
        "relationship_confidence": {},
        "narrative_intelligence": {},
        "character_identity_fusion": {},
    }
    base.update(kwargs)
    return CharacterEvolutionEngine.build(**base)


def test_detects_rank_change_from_timeline():
    result = build(
        character_timeline={
            "timelines": [{
                "events": [{
                    "event_type": "coronation",
                    "character_node_key": "character:arthur",
                    "sequence_index": 1,
                    "sentence": "Arthur wird zum König gekrönt.",
                    "confidence": 0.9,
                }]
            }]
        }
    )

    assert result["summary"]["character_count"] == 1
    assert (
        result["evolutions"][0]["changes"][0]["evolution_type"]
        == "rank_change"
    )
    assert result["automatic_import"] is False


def test_detects_alignment_change():
    result = build(
        narrative_intelligence={
            "relations": [{
                "source_node_key": "character:orm",
                "sentence": "Orm wechselt die Seite und verbündet sich mit Arthur.",
                "confidence": 0.8,
            }]
        }
    )

    assert (
        result["evolutions"][0]["changes"][0]["evolution_type"]
        == "alignment_change"
    )


def test_detects_conflicting_targets():
    result = build(
        narrative_intelligence={
            "changes": [
                {
                    "evolution_type": "rank_change",
                    "source_node_key": "character:arthur",
                    "to_value": "king",
                    "confidence": 0.8,
                },
                {
                    "evolution_type": "rank_change",
                    "source_node_key": "character:arthur",
                    "to_value": "emperor",
                    "confidence": 0.8,
                },
            ]
        }
    )

    assert result["summary"]["conflict_count"] == 1
    assert result["requires_confirmation"] is True


def test_no_changes_keeps_manual_safety():
    result = build()
    assert result["decision"]["status"] == "no_character_evolution"
    assert result["automatic_import"] is False
