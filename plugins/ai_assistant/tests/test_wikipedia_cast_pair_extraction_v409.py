import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_cast_resolver import CharacterCastResolver


SOURCE = {"id": "wiki"}
MAIN_NODE = {
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
    "confidence": 0.84,
    "metadata": {},
}


def test_wikipedia_markup_cast_pairs():
    text = (
        '"Besetzung":{"wt":"'
        '* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]\\n'
        '* [[Patrick Wilson]]: Orm Marius\\n'
        '* [[Yahya Abdul-Mateen II]]: David Kane / Black Manta'
        '"},"Synchronisation":{"wt":""}'
    )

    pairs = CharacterCastResolver()._extract_cast_pairs(text)

    assert pairs == [
        {
            "actor": "Jason Momoa",
            "role": "Arthur Curry / Aquaman",
            "evidence": "* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]",
            "source_format": "wikipedia_infobox_markup",
        },
        {
            "actor": "Patrick Wilson",
            "role": "Orm Marius",
            "evidence": "* [[Patrick Wilson]]: Orm Marius",
            "source_format": "wikipedia_infobox_markup",
        },
        {
            "actor": "Yahya Abdul-Mateen II",
            "role": "David Kane / Black Manta",
            "evidence": (
                "* [[Yahya Abdul-Mateen II]]: "
                "David Kane / Black Manta"
            ),
            "source_format": "wikipedia_infobox_markup",
        },
    ]


def test_flat_wikipedia_cast_pairs():
    text = (
        "Besetzung "
        "Jason Momoa : Arthur Curry / Aquaman "
        "Patrick Wilson : Orm Marius "
        "Amber Heard : Mera "
        "Yahya Abdul-Mateen II : David Kane / Black Manta "
        "Chronologie"
    )

    pairs = CharacterCastResolver()._extract_cast_pairs(text)

    assert [item["actor"] for item in pairs] == [
        "Jason Momoa",
        "Patrick Wilson",
        "Amber Heard",
        "Yahya Abdul-Mateen II",
    ]
    assert [item["role"] for item in pairs] == [
        "Arthur Curry / Aquaman",
        "Orm Marius",
        "Mera",
        "David Kane / Black Manta",
    ]


def test_resolver_creates_cast_and_alias_graph():
    text = (
        "Besetzung "
        "Jason Momoa : Arthur Curry / Aquaman "
        "Patrick Wilson : Orm Marius "
        "Yahya Abdul-Mateen II : David Kane / Black Manta "
        "Chronologie"
    )

    result = CharacterCastResolver().resolve(
        main_node=MAIN_NODE,
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert result["cast_pair_count"] == 3
    assert "person:jason momoa" in keys
    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert "person:yahya abdul-mateen ii" in keys
    assert "character:david kane" in keys
    assert "character_alias:black manta" in keys

    assert {
        "has_cast",
        "portrays",
        "portrayed_by",
        "appears_in",
        "alias_of",
    } <= edge_types


def test_no_cast_warning_disappears_when_pairs_exist():
    result = CharacterCastResolver().resolve(
        main_node=MAIN_NODE,
        text=(
            "Besetzung Jason Momoa : Arthur Curry / Aquaman "
            "Patrick Wilson : Orm Marius Chronologie"
        ),
        source=SOURCE,
    )

    assert result["cast_pair_count"] == 2
    assert "Keine sicheren Besetzungspaare gefunden." not in result["warnings"]
