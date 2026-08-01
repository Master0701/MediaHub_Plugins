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


def analyze(text):
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


def test_slug_replaces_underscores_with_hyphens():
    assert (
        FranchiseRelationIntelligence._slug(
            "alternate_timeline"
        )
        == "alternate-timeline"
    )


def test_non_canon_key():
    result = analyze("Die Geschichte ist non-canon.")

    assert "canon:non-canon" in node_keys(result)


def test_alternate_timeline_key():
    result = analyze(
        "Die Handlung spielt in einer alternative Zeitlinie."
    )

    assert (
        "timeline:alternate-timeline"
        in node_keys(result)
    )


def test_parallel_universe_key():
    result = analyze(
        "Die Geschichte spielt in einem parallelen Universum."
    )

    assert (
        "timeline:parallel-universe"
        in node_keys(result)
    )


def test_prime_timeline_key():
    result = analyze(
        "Die Serie gehört zur Prime Timeline."
    )

    assert (
        "timeline:prime-timeline"
        in node_keys(result)
    )


def test_kelvin_timeline_key():
    result = analyze(
        "Der Film spielt in der Kelvin Timeline."
    )

    assert (
        "timeline:kelvin-timeline"
        in node_keys(result)
    )


def test_strategy_v441():
    result = analyze("Die Geschichte ist non-canon.")

    assert result["strategy"] == (
        "franchise_relation_intelligence_v441"
    )
