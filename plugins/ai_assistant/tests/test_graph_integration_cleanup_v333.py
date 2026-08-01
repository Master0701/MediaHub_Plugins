import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_cast_resolver import CharacterCastResolver
from services.universe_franchise_builder import UniverseFranchiseBuilder


MAIN = {
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
    "confidence": 0.89,
    "metadata": {},
}
SOURCE = {"id": "wiki"}


def test_real_universe_sentence_has_clean_keys():
    result = UniverseFranchiseBuilder().build(
        main_node=MAIN,
        text=(
            "Es ist der 15. und letzte Film des DC Extended Universe, "
            "das 2024 durch das DC Universe ersetzt wurde."
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "universe:dc extended universe" in keys
    assert "universe:dc universe" in keys
    assert not any("letzte film des" in key for key in keys)

    assert any(
        edge["edge_type"] == "replaced_by"
        and edge["source_node_key"] == "universe:dc extended universe"
        and edge["target_node_key"] == "universe:dc universe"
        for edge in result["edges"]
    )


def test_movie_does_not_get_bad_atlantis_location():
    result = UniverseFranchiseBuilder().build(
        main_node=MAIN,
        text=(
            "Einige Jahre nachdem er König von Atlantis geworden war, "
            "heiratete Arthur Curry Mera."
        ),
        source=SOURCE,
    )

    assert not any(
        edge["edge_type"] == "located_in"
        for edge in result["edges"]
    )
    assert not any(
        "atlantis geworden war" in node["key"]
        for node in result["nodes"]
    )


def test_embedded_wikipedia_cast_is_resolved():
    text = (
        r'\"Besetzung\":{\"wt\":\"'
        r'* [[Jason Momoa]]: Arthur Curry / [[Aquaman]]\\n'
        r'* [[Patrick Wilson]]: Orm Marius\\n'
        r'* [[Yahya Abdul-Mateen II]]: David Kane / Black Manta'
        r'\"},\"Synchronisation\":{\"wt\":\"\"}'
    )

    result = CharacterCastResolver().resolve(
        main_node=MAIN,
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "person:jason momoa" in keys
    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert "person:patrick wilson" in keys
    assert "character:orm marius" in keys
    assert {"portrayed_by", "appears_in", "alias_of"} <= edge_types
