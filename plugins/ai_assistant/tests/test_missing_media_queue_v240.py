import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.missing_media_queue import (
    MissingMediaQueue,
)


def _result():
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


def test_missing_items_are_persistent_and_deduplicated(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    queue = MissingMediaQueue(database)

    first = queue.add_from_completeness(_result())
    second = queue.add_from_completeness(_result())

    assert first["created_count"] == 1
    assert second["created_count"] == 0
    assert second["existing_count"] == 1

    reopened = MissingMediaQueue(database)
    assert len(reopened.list("pending")) == 1


def test_missing_item_statuses_are_supported(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_result())
    item_id = queue.list()[0]["id"]

    wanted = queue.set_status(item_id, "wanted")
    assert wanted["status"] == "wanted"

    resolved = queue.set_status(item_id, "resolved")
    assert resolved["status"] == "resolved"
    assert queue.list("pending") == []
