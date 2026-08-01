import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_cast_resolver import CharacterCastResolver


MAIN = {
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
    "confidence": 0.89,
    "metadata": {},
}
SOURCE = {"id": "wiki"}


def test_cast_intelligence_creates_bidirectional_relations():
    text = (
        r'\"Besetzung\":{\"wt\":\"'
        r'* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]\\n'
        r'* [[Patrick Wilson]]: Orm Marius'
        r'\"},\"Synchronisation\":{\"wt\":\"\"}'
    )

    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert result["strategy"] == "character_cast_intelligence_v340"
    assert result["cast_pair_count"] == 2
    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "person:jason momoa" in keys
    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert {
        "has_cast",
        "portrays",
        "portrayed_by",
        "appears_in",
        "alias_of",
    } <= edge_types


def test_voice_role_creates_voices_relation():
    text = (
        r'\"Besetzung\":{\"wt\":\"'
        r'* [[Martin Short]]: Kingfish (Stimme)'
        r'\"},\"Synchronisation\":{\"wt\":\"\"}'
    )

    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=text,
        source=SOURCE,
    )

    assert any(
        edge["edge_type"] == "voices"
        and edge["source_node_key"] == "person:martin short"
        and edge["target_node_key"] == "character:kingfish"
        for edge in result["edges"]
    )


def test_billing_position_is_preserved():
    text = (
        r'\"Besetzung\":{\"wt\":\"'
        r'* [[Jason Momoa]]: Arthur Curry / Aquaman\\n'
        r'* [[Patrick Wilson]]: Orm Marius'
        r'\"},\"Synchronisation\":{\"wt\":\"\"}'
    )

    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=text,
        source=SOURCE,
    )

    has_cast = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "has_cast"
    ]

    assert has_cast[0]["metadata"]["billing_position"] == 1
    assert has_cast[1]["metadata"]["billing_position"] == 2
