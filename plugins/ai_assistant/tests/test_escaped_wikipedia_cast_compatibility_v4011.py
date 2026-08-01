import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_cast_resolver import CharacterCastResolver


SOURCE = {"id": "wiki"}
MAIN = {
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
    "confidence": 0.84,
    "metadata": {},
}


def test_escaped_json_markup_is_normalized():
    text = (
        r'\"Besetzung\":{\"wt\":\"'
        r'* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]\\n'
        r'* [[Patrick Wilson]]: Orm Marius'
        r'\"},\"Synchronisation\":{\"wt\":\"\"}'
    )

    pairs = CharacterCastResolver()._extract_cast_pairs(text)

    assert [(item["actor"], item["role"]) for item in pairs] == [
        ("Jason Momoa", "Arthur Curry / Aquaman"),
        ("Patrick Wilson", "Orm Marius"),
    ]


def test_voice_role_survives_normalization():
    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=(
            r'\"Besetzung\":{\"wt\":\"'
            r'* [[Martin Short]]: Kingfish (Stimme)'
            r'\"},\"Synchronisation\":{\"wt\":\"\"}'
        ),
        source=SOURCE,
    )

    assert any(
        edge["edge_type"] == "voices"
        and edge["source_node_key"] == "person:martin short"
        and edge["target_node_key"] == "character:kingfish"
        for edge in result["edges"]
    )


def test_billing_positions_are_preserved():
    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=(
            r'\"Besetzung\":{\"wt\":\"'
            r'* [[Jason Momoa]]: Arthur Curry / Aquaman\\n'
            r'* [[Patrick Wilson]]: Orm Marius'
            r'\"},\"Synchronisation\":{\"wt\":\"\"}'
        ),
        source=SOURCE,
    )

    has_cast = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "has_cast"
    ]

    assert [edge["metadata"]["billing_position"] for edge in has_cast] == [1, 2]


def test_public_strategy_remains_backward_compatible():
    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=(
            "Besetzung Jason Momoa : Arthur Curry / Aquaman "
            "Chronologie"
        ),
        source=SOURCE,
    )

    assert result["strategy"] == "character_cast_intelligence_v340"
