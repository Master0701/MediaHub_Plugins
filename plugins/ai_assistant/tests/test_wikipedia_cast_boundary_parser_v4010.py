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


def test_markup_backslash_n_lines_are_parsed():
    text = (
        '"Besetzung":{"wt":"'
        '* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]\\n'
        '* [[Patrick Wilson]]: Orm Marius\\n'
        '* [[Yahya Abdul-Mateen II]]: David Kane / Black Manta'
        '"},"Synchronisation":{"wt":""}'
    )

    pairs = CharacterCastResolver()._extract_cast_pairs(text)

    assert [(item["actor"], item["role"]) for item in pairs] == [
        ("Jason Momoa", "Arthur Curry / Aquaman"),
        ("Patrick Wilson", "Orm Marius"),
        ("Yahya Abdul-Mateen II", "David Kane / Black Manta"),
    ]


def test_flat_colon_blocks_are_parsed_without_greedy_actor_names():
    text = (
        "Besetzung "
        "Jason Momoa : Arthur Curry / Aquaman "
        "Patrick Wilson : Orm Marius "
        "Amber Heard : Mera "
        "Yahya Abdul-Mateen II : David Kane / Black Manta "
        "Chronologie"
    )

    pairs = CharacterCastResolver()._extract_cast_pairs(text)

    assert [(item["actor"], item["role"]) for item in pairs] == [
        ("Jason Momoa", "Arthur Curry / Aquaman"),
        ("Patrick Wilson", "Orm Marius"),
        ("Amber Heard", "Mera"),
        ("Yahya Abdul-Mateen II", "David Kane / Black Manta"),
    ]


def test_suffix_actor_boundary():
    split = CharacterCastResolver._split_trailing_actor(
        "Mera Yahya Abdul-Mateen II"
    )

    assert split == ("Mera", "Yahya Abdul-Mateen II")


def test_two_word_actor_boundary():
    split = CharacterCastResolver._split_trailing_actor(
        "Orm Marius Amber Heard"
    )

    assert split == ("Orm Marius", "Amber Heard")


def test_resolver_builds_complete_cast_graph():
    result = CharacterCastResolver().resolve(
        main_node=MAIN_NODE,
        text=(
            "Besetzung "
            "Jason Momoa : Arthur Curry / Aquaman "
            "Patrick Wilson : Orm Marius "
            "Yahya Abdul-Mateen II : David Kane / Black Manta "
            "Chronologie"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert result["cast_pair_count"] == 3
    assert "person:jason momoa" in keys
    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert "person:patrick wilson" in keys
    assert "character:orm marius" in keys
    assert "person:yahya abdul-mateen ii" in keys
    assert "character:david kane" in keys
    assert "character_alias:black manta" in keys
