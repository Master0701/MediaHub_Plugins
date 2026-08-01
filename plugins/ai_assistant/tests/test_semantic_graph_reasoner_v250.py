import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.semantic_graph_reasoner import (
    SemanticGraphReasoner,
)


def test_confirmed_group_metadata_creates_proposal(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity(
        {
            "title": "Aquaman",
            "media_type": "movie",
            "year": 2018,
            "metadata": {
                "franchise": "Aquaman",
                "universe": "DC Extended Universe",
            },
        }
    )

    result = SemanticGraphReasoner(engine).reason()
    group_types = {
        item["relation_type"]
        for item in result["proposals"]
        if item["kind"] == "group_membership"
    }

    assert group_types == {"franchise", "universe"}
    assert result["automatic_changes"] is False
    assert result["requires_confirmation"] is True


def test_shared_group_and_order_support_sequel_proposal(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    first = engine.upsert_identity(
        {
            "title": "Testfilm",
            "media_type": "movie",
            "year": 2018,
            "metadata": {"franchise": "Testreihe"},
        }
    )["entity"]
    second = engine.upsert_identity(
        {
            "title": "Testfilm 2",
            "media_type": "movie",
            "year": 2023,
            "metadata": {"franchise": "Testreihe"},
        }
    )["entity"]
    engine.create_order(
        "Testreihe – Veröffentlichung",
        "release",
        [first["id"], second["id"]],
    )

    result = SemanticGraphReasoner(engine).reason()
    sequels = [
        item
        for item in result["proposals"]
        if item.get("relation_type") == "sequel"
    ]

    assert len(sequels) == 1
    assert sequels[0]["source_title"] == "Testfilm"
    assert sequels[0]["target_title"] == "Testfilm 2"
    assert sequels[0]["confidence"] >= 0.72
    assert sequels[0]["evidence"]


def test_existing_relation_is_not_proposed_again(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    first = engine.upsert_identity(
        {
            "title": "Testfilm",
            "media_type": "movie",
            "year": 2018,
            "metadata": {"franchise": "Testreihe"},
        }
    )["entity"]
    second = engine.upsert_identity(
        {
            "title": "Testfilm 2",
            "media_type": "movie",
            "year": 2023,
            "metadata": {"franchise": "Testreihe"},
        }
    )["entity"]
    engine.connect(
        first["id"],
        second["id"],
        "sequel",
    )

    result = SemanticGraphReasoner(engine).reason()

    assert not any(
        item.get("kind") == "direct_relation"
        and item.get("source_id") == first["id"]
        and item.get("target_id") == second["id"]
        and item.get("relation_type") == "sequel"
        for item in result["proposals"]
    )
    assert result["skipped_existing_relation_count"] >= 1
