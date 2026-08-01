import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_collection_intelligence import (
    FranchiseCollectionIntelligence,
)


SOURCE = {"id": "wiki"}


def test_explicit_franchise_survives_duplicate_deduplication():
    result = FranchiseCollectionIntelligence.analyze(
        main_node={
            "key": "movie:aquaman:2018",
            "node_type": "movie",
            "title": "Aquaman",
            "year": 2018,
        },
        classified_fields={
            "primary_values": {
                "franchise": "Aquaman",
                "franchise_installments": [
                    {"title": "Aquaman", "year": 2018},
                    {"title": "Aquaman", "year": 2018},
                ],
            }
        },
        relationship_proposal={"edges": []},
        universe_proposal={"edges": []},
        source=SOURCE,
    )

    assert result["franchise_count"] == 1
    assert result["installment_count"] == 1
    assert result["franchise_key"] == "franchise:aquaman"


def test_implicit_single_media_still_does_not_create_franchise():
    result = FranchiseCollectionIntelligence.analyze(
        main_node={
            "key": "movie:single:2020",
            "node_type": "movie",
            "title": "Single",
            "year": 2020,
        },
        classified_fields={"primary_values": {}},
        relationship_proposal={"edges": []},
        universe_proposal={"edges": []},
        source=SOURCE,
    )

    assert result["franchise_count"] == 0
    assert result["installment_count"] == 0


def test_strategy_v422():
    result = FranchiseCollectionIntelligence.analyze(
        main_node={
            "key": "movie:aquaman:2018",
            "node_type": "movie",
            "title": "Aquaman",
            "year": 2018,
        },
        classified_fields={
            "primary_values": {
                "franchise": "Aquaman",
            }
        },
        relationship_proposal={"edges": []},
        universe_proposal={"edges": []},
        source=SOURCE,
    )

    assert result["strategy"] == (
        "franchise_collection_intelligence_v422"
    )
