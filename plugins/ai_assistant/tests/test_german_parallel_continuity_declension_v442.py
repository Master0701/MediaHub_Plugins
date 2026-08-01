import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_relation_intelligence import (
    FranchiseRelationIntelligence,
)


MAIN = {
    "key": "movie:example:2024",
    "node_type": "movie",
    "title": "Example",
    "year": 2024,
}
SOURCE = {"id": "test"}


def analyze(text: str):
    return FranchiseRelationIntelligence.analyze(
        main_node=MAIN,
        text=text,
        source=SOURCE,
        relationship_proposal={"edges": []},
        franchise_collection={},
    )


def node_keys(result):
    return {
        node["key"]
        for node in result["nodes"]
    }


def test_parallel_without_ending():
    result = analyze(
        "Die Handlung spielt im parallel Universum."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_parallele_zeitlinie():
    result = analyze(
        "Die Handlung spielt in einer parallele Zeitlinie."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_parallelen_universum():
    result = analyze(
        "Die Geschichte spielt in einem parallelen Universum."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_paralleler_zeitlinie():
    result = analyze(
        "Die Geschichte folgt einer paralleler Zeitlinie."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_paralleles_universum():
    result = analyze(
        "Die Geschichte spielt in einem paralleles Universum."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_unrelated_parallel_word_does_not_match():
    result = analyze(
        "Die Produktion arbeitete parallel an mehreren Szenen."
    )

    assert (
        "timeline:parallel-universe"
        not in node_keys(result)
    )


def test_strategy_v442():
    result = analyze(
        "Die Geschichte spielt in einem parallelen Universum."
    )

    assert result["strategy"] == (
        "franchise_relation_intelligence_v442"
    )


def test_confirmation_safety_is_preserved():
    result = analyze(
        "Die Geschichte spielt in einem parallelen Universum."
    )

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        node["requires_confirmation"] is True
        and node["automatic_import"] is False
        for node in result["nodes"]
    )
    assert all(
        edge["requires_confirmation"] is True
        and edge["automatic_import"] is False
        for edge in result["edges"]
    )
