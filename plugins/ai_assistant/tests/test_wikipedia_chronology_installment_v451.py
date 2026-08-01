import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.timeline_order_intelligence import (
    TimelineOrderIntelligence,
)


MAIN = {
    "key": "movie:aquaman: lost kingdom:2023",
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
}
SOURCE = {"id": "wikipedia-test"}


def analyze(text):
    return TimelineOrderIntelligence.analyze(
        main_node=MAIN,
        text=text,
        source=SOURCE,
        franchise_collection={
            "franchise_name": "Aquaman",
        },
        franchise_relations={},
    )


def edge_types(result):
    return {
        edge["edge_type"]
        for edge in result["edges"]
    }


def node_keys(result):
    return {
        node["key"]
        for node in result["nodes"]
    }


def test_wikipedia_left_arrow_predecessor():
    result = analyze(
        "Chronologie ← Blue Beetle "
        "Aquaman: Lost Kingdom ist ein Film."
    )

    assert "predecessor_of" in edge_types(result)
    assert "movie:blue beetle" in node_keys(result)


def test_wikipedia_unicode_arrow_with_spacing():
    result = analyze(
        "Chronologie   ←   Blue Beetle"
    )

    assert "predecessor_of" in edge_types(result)


def test_wikipedia_ascii_arrow_predecessor():
    result = analyze(
        "Chronologie <- Blue Beetle"
    )

    assert "predecessor_of" in edge_types(result)


def test_installment_with_and_last_phrase():
    result = analyze(
        "Es ist der 15. und letzte Film "
        "des DC Extended Universe."
    )

    assert result["installment_number"] == 15
    assert any(
        item["kind"] == "installment_position"
        and item["position"] == 15
        and item["group"] == "DC Extended Universe"
        for item in result["observations"]
    )


def test_installment_plain_phrase_still_works():
    result = analyze(
        "Es ist der 15. Film des DC Extended Universe."
    )

    assert result["installment_number"] == 15


def test_installment_first_and_last_phrase():
    result = analyze(
        "Es ist der 1. und letzte Teil der Testreihe."
    )

    assert result["installment_number"] == 1


def test_wikipedia_chronology_and_installment_bundle():
    result = analyze(
        "Chronologie ← Blue Beetle "
        "Es ist der 15. und letzte Film "
        "des DC Extended Universe."
    )

    assert result["installment_number"] == 15
    assert "predecessor_of" in edge_types(result)
    assert result["edge_count"] >= 1
    assert result["node_count"] >= 1


def test_strategy_is_current():
    result = analyze(
        "Chronologie ← Blue Beetle"
    )

    assert result["strategy"] == (
        "timeline_order_intelligence_v452"
    )


def test_confirmation_safety():
    result = analyze(
        "Chronologie ← Blue Beetle "
        "Es ist der 15. und letzte Film "
        "des DC Extended Universe."
    )

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        edge["automatic_import"] is False
        and edge["requires_confirmation"] is True
        for edge in result["edges"]
    )
