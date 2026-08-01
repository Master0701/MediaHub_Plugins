import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine, OrderType, RelationType


def test_upsert_identity_is_idempotent_and_merges_aliases(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    first = engine.upsert_identity(
        {
            "title": "Aquaman and the Lost Kingdom",
            "media_type": "movie",
            "year": 2023,
            "aliases": ["Aquaman 2"],
            "external_ids": {"tmdb": "572802"},
        },
        confirmed_by_user=True,
    )
    second = engine.upsert_identity(
        {
            "title": "Aquaman and the Lost Kingdom",
            "media_type": "movie",
            "year": 2023,
            "aliases": ["Aquaman: Lost Kingdom"],
            "external_ids": {"imdb": "tt9663764"},
        },
        confirmed_by_user=True,
    )

    assert first["created"] is True
    assert second["created"] is False
    assert engine.stats()["entities"] == 1
    entity = engine.all_items()[0]
    assert {"Aquaman 2", "Aquaman: Lost Kingdom"} <= set(entity["aliases"])
    assert entity["external_ids"]["tmdb"] == "572802"
    assert entity["external_ids"]["imdb"] == "tt9663764"


def test_confirmed_relation_is_idempotent(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    first = engine.upsert_identity(
        {"title": "Aquaman", "media_type": "movie", "year": 2018}
    )["entity"]
    second = engine.upsert_identity(
        {
            "title": "Aquaman and the Lost Kingdom",
            "media_type": "movie",
            "year": 2023,
        }
    )["entity"]

    created = engine.connect_confirmed(
        first["id"],
        second["id"],
        RelationType.SEQUEL.value,
        confirmed_by_user=True,
    )
    repeated = engine.connect_confirmed(
        first["id"],
        second["id"],
        RelationType.SEQUEL.value,
        confirmed_by_user=True,
    )

    assert created["created"] is True
    assert repeated["created"] is False
    assert engine.stats()["relations"] == 1


def test_order_is_idempotent(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    one = engine.create_entity("Film 1", "movie")
    two = engine.create_entity("Film 2", "movie")

    first = engine.create_or_get_order(
        "Test Veröffentlichung",
        OrderType.RELEASE.value,
        [one["id"], two["id"]],
    )
    second = engine.create_or_get_order(
        "Test Veröffentlichung",
        OrderType.RELEASE.value,
        [one["id"], two["id"]],
    )

    assert first["created"] is True
    assert second["created"] is False
    assert engine.stats()["orders"] == 1


def test_proposals_are_not_persisted_as_relations(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    proposal = engine.propose_relationships(
        [
            {
                "title": "Aquaman",
                "media_type": "movie",
                "year": 2018,
                "universe": "DC Extended Universe",
            },
            {
                "title": "Aquaman and the Lost Kingdom",
                "media_type": "movie",
                "year": 2023,
                "relation_hints": [
                    {
                        "target_title": "Aquaman",
                        "relation_type": "sequel",
                        "confidence": 0.95,
                    }
                ],
            },
        ]
    )

    assert proposal["proposal_count"] == 2
    assert proposal["persisted_relations"] is False
    assert engine.stats()["relations"] == 0
