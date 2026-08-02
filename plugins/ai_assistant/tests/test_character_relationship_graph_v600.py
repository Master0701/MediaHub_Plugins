import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_relationship_graph import CharacterRelationshipGraph


def test_derives_inverse_parent_relation():
    result = CharacterRelationshipGraph.build(
        relationship_intelligence={
            "strategy": "relationship_intelligence",
            "conclusions": [
                {
                    "edge_type": "father_of",
                    "source_node_key": "character:arthur",
                    "target_node_key": "character:arthur-jr",
                    "confidence": 0.8,
                }
            ],
        },
        character_relationship_intelligence={},
        character_relationship_engine={},
        franchise_knowledge_graph={},
    )

    assert any(
        edge["edge_type"] == "child_of"
        and edge["source_node_key"] == "character:arthur-jr"
        for edge in result["edges"]
    )
    assert result["automatic_import"] is False


def test_derives_symmetric_friend_relation():
    result = CharacterRelationshipGraph.build(
        relationship_intelligence={},
        character_relationship_intelligence={
            "strategy": "character_relationship_intelligence",
            "conclusions": [
                {
                    "edge_type": "friend_of",
                    "source_node_key": "character:arthur",
                    "target_node_key": "character:orm",
                    "confidence": 0.7,
                }
            ],
        },
        character_relationship_engine={},
        franchise_knowledge_graph={},
    )

    assert any(
        edge["edge_type"] == "friend_of"
        and edge["source_node_key"] == "character:orm"
        and edge["target_node_key"] == "character:arthur"
        for edge in result["edges"]
    )


def test_detects_friend_enemy_conflict():
    payload = {
        "strategy": "test",
        "conclusions": [
            {
                "edge_type": "friend_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.8,
            },
            {
                "edge_type": "enemy_of",
                "source_node_key": "character:a",
                "target_node_key": "character:b",
                "confidence": 0.8,
            },
        ],
    }

    result = CharacterRelationshipGraph.build(
        relationship_intelligence=payload,
        character_relationship_intelligence={},
        character_relationship_engine={},
        franchise_knowledge_graph={},
    )

    assert result["summary"]["conflict_count"] == 1
