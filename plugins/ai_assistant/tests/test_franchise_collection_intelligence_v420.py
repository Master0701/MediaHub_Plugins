import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_collection_intelligence import (
    FranchiseCollectionIntelligence,
)


SOURCE = {"id": "wiki"}
MAIN = {
    "key": "movie:aquaman: lost kingdom:2023",
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
}


def result():
    return FranchiseCollectionIntelligence.analyze(
        main_node=MAIN,
        classified_fields={
            "primary_values": {
                "release_year": 2023,
                "predecessor": {
                    "title": "Aquaman",
                    "year": 2018,
                },
            }
        },
        relationship_proposal={
            "edges": [
                {
                    "edge_type": "sequel_of",
                    "source_node_key": MAIN["key"],
                    "target_node_key": "movie:aquaman:2018",
                }
            ]
        },
        universe_proposal={
            "edges": [
                {
                    "edge_type": "belongs_to",
                    "source_node_key": MAIN["key"],
                    "target_node_key": (
                        "universe:dc extended universe"
                    ),
                }
            ]
        },
        source=SOURCE,
    )


def test_aquaman_franchise_node_is_created():
    data = result()
    keys = {node["key"] for node in data["nodes"]}

    assert "franchise:aquaman" in keys
    assert data["franchise_count"] == 1


def test_both_movies_are_installments():
    data = result()
    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in data["edges"]
    }

    assert (
        "installment_of",
        "movie:aquaman: lost kingdom:2023",
        "franchise:aquaman",
    ) in edges
    assert (
        "installment_of",
        "movie:aquaman:2018",
        "franchise:aquaman",
    ) in edges
    assert data["installment_count"] == 2


def test_franchise_inherits_universe_membership():
    data = result()
    edges = {
        (
            edge["edge_type"],
            edge["source_node_key"],
            edge["target_node_key"],
        )
        for edge in data["edges"]
    }

    assert (
        "belongs_to",
        "franchise:aquaman",
        "universe:dc extended universe",
    ) in edges


def test_no_franchise_without_secure_relation():
    data = FranchiseCollectionIntelligence.analyze(
        main_node=MAIN,
        classified_fields={"primary_values": {}},
        relationship_proposal={"edges": []},
        universe_proposal={},
        source=SOURCE,
    )

    assert data["franchise_count"] == 0
    assert data["nodes"] == []
    assert data["edges"] == []


def test_results_require_confirmation():
    data = result()

    assert data["strategy"].startswith(
        "franchise_collection_intelligence_v"
    )
    assert data["automatic_import"] is False
    assert data["requires_confirmation"] is True
