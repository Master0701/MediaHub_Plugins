import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.timeline_order_intelligence import (
    TimelineOrderIntelligence,
)


SOURCE = {"id": "test-source"}
MAIN = {
    "key": "movie:example two:2024",
    "node_type": "movie",
    "title": "Example Two",
    "year": 2024,
}


def analyze(text, main=None, franchise=None):
    return TimelineOrderIntelligence.analyze(
        main_node=main or MAIN,
        text=text,
        source=SOURCE,
        franchise_collection=franchise or {},
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


def test_chronologically_before():
    result = analyze(
        "Der Film spielt chronologisch vor Example Three."
    )

    assert "precedes_chronologically" in edge_types(result)
    assert "movie:example three" in node_keys(result)


def test_chronologically_after():
    result = analyze(
        "Der Film spielt chronologisch nach Example One."
    )

    assert "follows_chronologically" in edge_types(result)


def test_release_before():
    result = analyze(
        "Der Film erschien vor Example Three."
    )

    assert "precedes_in_release" in edge_types(result)


def test_release_after():
    result = analyze(
        "Der Film erschien nach Example One."
    )

    assert "follows_in_release" in edge_types(result)


def test_predecessor_direction():
    result = analyze(
        "Der Vorgänger ist Example One."
    )

    edges = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "predecessor_of"
    ]

    assert len(edges) == 1
    assert (
        edges[0]["source_node_key"]
        == "movie:example one"
    )
    assert (
        edges[0]["target_node_key"]
        == MAIN["key"]
    )


def test_successor_direction():
    result = analyze(
        "Der Nachfolger ist Example Three."
    )

    edges = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "successor_of"
    ]

    assert len(edges) == 1
    assert (
        edges[0]["source_node_key"]
        == MAIN["key"]
    )
    assert (
        edges[0]["target_node_key"]
        == "movie:example three"
    )


def test_target_year_is_preserved():
    result = analyze(
        "Der Film erschien nach Example One aus dem Jahr 2020."
    )

    assert "movie:example one:2020" in node_keys(result)


def test_chronological_order_arrow_list():
    result = analyze(
        "Chronologische Reihenfolge: "
        "Example One → Example Two → Example Three"
    )

    assert result["order_count"] == 1
    order = result["orders"][0]

    assert order["order_type"] == "chronological"
    assert [
        item["title"]
        for item in order["items"]
    ] == [
        "Example One",
        "Example Two",
        "Example Three",
    ]


def test_release_order_comma_list():
    result = analyze(
        "Veröffentlichungsreihenfolge: "
        "Example One, Example Two, Example Three"
    )

    assert result["order_count"] == 1
    assert (
        result["orders"][0]["order_type"]
        == "release"
    )


def test_production_order_heading():
    result = analyze(
        "Produktionsreihenfolge: "
        "Pilot > Season One > Season Two"
    )

    assert result["order_count"] == 1
    assert (
        result["orders"][0]["order_type"]
        == "release"
    )


def test_order_node_uses_franchise_name():
    result = analyze(
        "Chronologische Reihenfolge: "
        "One > Two > Three",
        franchise={
            "franchise_name": "Example Franchise",
        },
    )

    assert (
        "order:example-franchise:chronological"
        in node_keys(result)
    )


def test_order_item_positions():
    result = analyze(
        "Chronologische Reihenfolge: "
        "One > Two > Three"
    )

    positions = sorted(
        edge["metadata"]["position"]
        for edge in result["edges"]
        if edge["edge_type"] == "has_order_item"
    )

    assert positions == [1, 2, 3]


def test_duplicate_order_items_are_removed():
    result = analyze(
        "Chronologische Reihenfolge: "
        "One > Two > One > Three"
    )

    assert [
        item["title"]
        for item in result["orders"][0]["items"]
    ] == ["One", "Two", "Three"]


def test_installment_position():
    result = analyze(
        "Der Film ist der 15. Film des DC Extended Universe."
    )

    assert result["installment_number"] == 15
    assert any(
        item["kind"] == "installment_position"
        for item in result["observations"]
    )


def test_no_false_order_from_plain_sentence():
    result = analyze(
        "Die Produktion begann nach einer längeren Pause."
    )

    assert result["order_count"] == 0
    assert result["edge_count"] == 0


def test_confirmation_gate():
    result = analyze(
        "Der Film erschien nach Example One."
    )

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        edge["automatic_import"] is False
        and edge["requires_confirmation"] is True
        for edge in result["edges"]
    )


def test_strategy_is_current():
    result = analyze(
        "Der Film erschien nach Example One."
    )

    assert result["strategy"].startswith(
        "timeline_order_intelligence_v"
    )


def test_relation_counts():
    result = analyze(
        "Der Film erschien nach Example One. "
        "Der Nachfolger ist Example Three."
    )

    assert result["relation_counts"][
        "follows_in_release"
    ] == 1
    assert result["relation_counts"][
        "successor_of"
    ] == 1
