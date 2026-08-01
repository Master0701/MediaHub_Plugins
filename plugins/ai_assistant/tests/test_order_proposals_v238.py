import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.order_proposals import (
    KnowledgeGraphOrderProposalService,
)


def test_release_order_is_sorted_by_year(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity(
        {
            "title": "Teil 2",
            "media_type": "movie",
            "year": 2023,
            "metadata": {"franchise": "Testreihe"},
        }
    )
    engine.upsert_identity(
        {
            "title": "Teil 1",
            "media_type": "movie",
            "year": 2018,
            "metadata": {"franchise": "Testreihe"},
        }
    )

    result = KnowledgeGraphOrderProposalService(engine).propose()

    assert result["proposal_count"] == 1
    proposal = result["proposals"][0]
    assert proposal["order_type"] == "release"
    assert proposal["entity_titles"] == ["Teil 1", "Teil 2"]
    assert result["persisted_orders"] is False


def test_chronological_order_requires_all_indices(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity(
        {
            "title": "Später veröffentlicht",
            "media_type": "movie",
            "year": 2020,
            "metadata": {
                "franchise": "Chrono",
                "chronology_index": 1,
            },
        }
    )
    engine.upsert_identity(
        {
            "title": "Früher veröffentlicht",
            "media_type": "movie",
            "year": 2010,
            "metadata": {
                "franchise": "Chrono",
                "chronology_index": 2,
            },
        }
    )

    result = KnowledgeGraphOrderProposalService(engine).propose()
    chronological = [
        item for item in result["proposals"]
        if item["order_type"] == "chronological"
    ]

    assert len(chronological) == 1
    assert chronological[0]["entity_titles"] == [
        "Später veröffentlicht",
        "Früher veröffentlicht",
    ]
