import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_relationship_intelligence import CharacterRelationshipIntelligence


def test_detects_german_family_and_mentor_relations():
    result = CharacterRelationshipIntelligence.analyze(
        main_node={"key": "series:test", "node_type": "series", "title": "Test"},
        text="Orm ist der Bruder von Arthur Curry. Gibbs ist der Mentor von Timothy McGee.",
        source={"id": "source-1"},
    )
    edge_types = {item["edge_type"] for item in result["edges"]}
    assert {"brother_of", "mentor_of"} <= edge_types
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True


def test_detects_english_relationships():
    result = CharacterRelationshipIntelligence.analyze(
        main_node={"key": "series:test", "node_type": "series", "title": "Test"},
        text="Spock is a friend of James Kirk. Batman is an enemy of Joker.",
        source={"id": "source-2"},
    )
    edge_types = {item["edge_type"] for item in result["edges"]}
    assert {"friend_of", "enemy_of"} <= edge_types
