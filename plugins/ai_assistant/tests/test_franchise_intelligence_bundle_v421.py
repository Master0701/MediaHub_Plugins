import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_collection_intelligence import (
    FranchiseCollectionIntelligence,
)


SOURCE = {"id": "wiki"}


def analyze(
    *,
    main_node,
    primary_values,
    relation_edges=None,
    universe_edges=None,
):
    return FranchiseCollectionIntelligence.analyze(
        main_node=main_node,
        classified_fields={"primary_values": primary_values},
        relationship_proposal={
            "edges": relation_edges or [],
        },
        universe_proposal={
            "edges": universe_edges or [],
        },
        source=SOURCE,
    )


def edge_tuples(result):
    return {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in result["edges"]
    }


def test_aquaman_two_part_franchise():
    result = analyze(
        main_node={
            "key": "movie:aquaman: lost kingdom:2023",
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "year": 2023,
        },
        primary_values={
            "release_year": 2023,
            "predecessor": {
                "title": "Aquaman",
                "year": 2018,
            },
        },
        relation_edges=[{
            "edge_type": "sequel_of",
            "source_node_key": "movie:aquaman: lost kingdom:2023",
            "target_node_key": "movie:aquaman:2018",
        }],
    )

    assert result["franchise_key"] == "franchise:aquaman"
    assert result["installment_count"] == 2
    assert {
        "movie:aquaman:2018",
        "movie:aquaman: lost kingdom:2023",
    } <= {
        item["source_node_key"]
        for item in result["edges"]
        if item["edge_type"] == "installment_of"
    }


def test_multiple_installments_are_supported():
    result = analyze(
        main_node={
            "key": "movie:rocky v:1990",
            "node_type": "movie",
            "title": "Rocky V",
            "year": 1990,
        },
        primary_values={
            "franchise": "Rocky",
            "franchise_installments": [
                {"title": "Rocky", "year": 1976},
                {"title": "Rocky II", "year": 1979},
                {"title": "Rocky III", "year": 1982},
                {"title": "Rocky IV", "year": 1985},
            ],
        },
    )

    assert result["franchise_key"] == "franchise:rocky"
    assert result["installment_count"] == 5


def test_release_order_uses_year_when_no_explicit_index():
    result = analyze(
        main_node={
            "key": "movie:part three:2003",
            "node_type": "movie",
            "title": "Part Three",
            "year": 2003,
        },
        primary_values={
            "franchise": "Example",
            "franchise_installments": [
                {"title": "Part One", "year": 2001},
                {"title": "Part Two", "year": 2002},
            ],
        },
    )

    assert [item["year"] for item in result["release_order"]] == [
        2001,
        2002,
        2003,
    ]


def test_explicit_release_index_overrides_year():
    result = analyze(
        main_node={
            "key": "movie:b:2000",
            "node_type": "movie",
            "title": "B",
            "year": 2000,
        },
        primary_values={
            "franchise": "Example",
            "release_index": 2,
            "franchise_installments": [
                {
                    "title": "A",
                    "year": 2005,
                    "release_index": 1,
                },
            ],
        },
    )

    assert [item["title"] for item in result["release_order"]] == [
        "A",
        "B",
    ]


def test_chronology_order_is_separate_from_release_order():
    result = analyze(
        main_node={
            "key": "movie:second released:2000",
            "node_type": "movie",
            "title": "Second Released",
            "year": 2000,
        },
        primary_values={
            "franchise": "Example",
            "release_index": 2,
            "chronology_index": 1,
            "franchise_installments": [
                {
                    "title": "First Released",
                    "year": 1990,
                    "release_index": 1,
                    "chronology_index": 2,
                },
            ],
        },
    )

    assert [item["title"] for item in result["release_order"]] == [
        "First Released",
        "Second Released",
    ]
    assert [item["title"] for item in result["chronology_order"]] == [
        "Second Released",
        "First Released",
    ]


def test_prequel_relation_is_preserved():
    result = analyze(
        main_node={
            "key": "movie:prequel:2020",
            "node_type": "movie",
            "title": "Prequel",
            "year": 2020,
        },
        primary_values={
            "franchise": "Example",
            "franchise_installments": [
                {"title": "Original", "year": 2010},
            ],
        },
        relation_edges=[{
            "edge_type": "prequel_of",
            "source_node_key": "movie:prequel:2020",
            "target_node_key": "movie:original:2010",
        }],
    )

    assert (
        "prequel_of",
        "movie:prequel:2020",
        "movie:original:2010",
    ) in edge_tuples(result)


def test_spin_off_relation_is_preserved():
    result = analyze(
        main_node={
            "key": "movie:creed:2015",
            "node_type": "movie",
            "title": "Creed",
            "year": 2015,
        },
        primary_values={
            "franchise": "Rocky",
            "franchise_installments": [
                {"title": "Rocky", "year": 1976},
            ],
        },
        relation_edges=[{
            "edge_type": "spin_off_of",
            "source_node_key": "movie:creed:2015",
            "target_node_key": "movie:rocky:1976",
        }],
    )

    assert (
        "spin_off_of",
        "movie:creed:2015",
        "movie:rocky:1976",
    ) in edge_tuples(result)


def test_crossover_relation_is_preserved():
    result = analyze(
        main_node={
            "key": "movie:crossover:2020",
            "node_type": "movie",
            "title": "Crossover",
            "year": 2020,
        },
        primary_values={
            "franchise": "Shared Event",
            "franchise_installments": [
                {"title": "Other Series Film", "year": 2019},
            ],
        },
        relation_edges=[{
            "edge_type": "crossover_with",
            "source_node_key": "movie:crossover:2020",
            "target_node_key": "movie:other series film:2019",
        }],
    )

    assert (
        "crossover_with",
        "movie:crossover:2020",
        "movie:other series film:2019",
    ) in edge_tuples(result)


def test_duplicate_installments_are_removed():
    result = analyze(
        main_node={
            "key": "movie:aquaman:2018",
            "node_type": "movie",
            "title": "Aquaman",
            "year": 2018,
        },
        primary_values={
            "franchise": "Aquaman",
            "franchise_installments": [
                {"title": "Aquaman", "year": 2018},
                {"title": "Aquaman", "year": 2018},
            ],
        },
    )

    assert result["installment_count"] == 1


def test_same_title_different_years_are_kept_separate():
    result = analyze(
        main_node={
            "key": "movie:example:2020",
            "node_type": "movie",
            "title": "Example",
            "year": 2020,
        },
        primary_values={
            "franchise": "Example",
            "franchise_installments": [
                {"title": "Example", "year": 1980},
            ],
        },
    )

    assert result["installment_count"] == 2


def test_missing_year_is_supported():
    result = analyze(
        main_node={
            "key": "movie:unknown",
            "node_type": "movie",
            "title": "Unknown",
            "year": None,
        },
        primary_values={
            "franchise": "Unknown",
            "franchise_installments": [
                {"title": "Unknown Part 2", "year": 2022},
            ],
        },
    )

    assert result["installment_count"] == 2
    assert any(
        item["year"] is None
        for item in result["release_order"]
    )


def test_multiple_universe_memberships_are_supported():
    main = {
        "key": "movie:crossover:2020",
        "node_type": "movie",
        "title": "Crossover",
        "year": 2020,
    }
    result = analyze(
        main_node=main,
        primary_values={
            "franchise": "Shared Event",
            "franchise_installments": [
                {"title": "Other", "year": 2019},
            ],
        },
        universe_edges=[
            {
                "edge_type": "belongs_to",
                "source_node_key": main["key"],
                "target_node_key": "universe:a",
            },
            {
                "edge_type": "belongs_to",
                "source_node_key": main["key"],
                "target_node_key": "universe:b",
            },
        ],
    )

    edges = edge_tuples(result)
    assert (
        "belongs_to",
        "franchise:shared event",
        "universe:a",
    ) in edges
    assert (
        "belongs_to",
        "franchise:shared event",
        "universe:b",
    ) in edges


def test_no_franchise_without_secure_evidence():
    result = analyze(
        main_node={
            "key": "movie:single:2020",
            "node_type": "movie",
            "title": "Single",
            "year": 2020,
        },
        primary_values={},
    )

    assert result["franchise_count"] == 0
    assert result["nodes"] == []
    assert result["edges"] == []


def test_every_generated_item_requires_confirmation():
    result = analyze(
        main_node={
            "key": "movie:b:2002",
            "node_type": "movie",
            "title": "B",
            "year": 2002,
        },
        primary_values={
            "franchise": "Example",
            "franchise_installments": [
                {"title": "A", "year": 2001},
            ],
        },
    )

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        node.get("requires_confirmation") is True
        for node in result["nodes"]
    )
    assert all(
        edge.get("requires_confirmation") is True
        for edge in result["edges"]
    )


def test_strategy_is_v421_and_v420_shape_is_preserved():
    result = analyze(
        main_node={
            "key": "movie:b:2002",
            "node_type": "movie",
            "title": "B",
            "year": 2002,
        },
        primary_values={
            "franchise": "Example",
            "franchise_installments": [
                {"title": "A", "year": 2001},
            ],
        },
    )

    assert result["strategy"].startswith(
        "franchise_collection_intelligence_v"
    )
    for key in (
        "schema_version",
        "franchise_count",
        "installment_count",
        "franchise_key",
        "nodes",
        "edges",
        "automatic_import",
        "requires_confirmation",
    ):
        assert key in result
