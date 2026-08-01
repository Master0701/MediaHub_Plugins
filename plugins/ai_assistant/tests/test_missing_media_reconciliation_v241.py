import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.missing_media_queue import (
    MissingMediaQueue,
)


def _completeness():
    return {
        "groups": [
            {
                "group_type": "franchise",
                "group_name": "Aquaman",
                "missing": [
                    {
                        "title": "Aquaman and the Lost Kingdom",
                        "year": 2023,
                        "media_type": "movie",
                    }
                ],
            }
        ]
    }


def test_matching_entity_resolves_missing_item(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_completeness())

    result = queue.reconcile_entity(
        {
            "id": "entity-1",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
            "media_type": "movie",
            "aliases": [],
        }
    )

    assert result["resolved_count"] == 1
    item = queue.list()[0]
    assert item["status"] == "resolved"
    assert item["resolved_entity_id"] == "entity-1"


def test_alias_can_resolve_missing_item(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_completeness())

    result = queue.reconcile_entity(
        {
            "id": "entity-2",
            "title": "Aquaman 2",
            "year": 2023,
            "media_type": "movie",
            "aliases": ["Aquaman and the Lost Kingdom"],
        }
    )

    assert result["resolved_count"] == 1


def test_wrong_year_does_not_resolve(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_completeness())

    result = queue.reconcile_entity(
        {
            "id": "entity-3",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2018,
            "media_type": "movie",
        }
    )

    assert result["resolved_count"] == 0
    assert queue.list()[0]["status"] == "pending"
