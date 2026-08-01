import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.missing_media_handoff import (
    MissingMediaHandoffService,
)
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


def test_handoff_is_safe_and_versioned(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    queue = MissingMediaQueue(database)
    queue.add_from_completeness(_completeness())
    service = MissingMediaHandoffService(queue, database)

    payload = service.create_handoff(
        target_plugin="mediahub.list_export",
    )

    assert payload["producer_version"] == "2.4.3"
    assert payload["target_plugin"] == "mediahub.list_export"
    assert payload["safety"]["queue_write_access"] is False
    assert payload["safety"]["automatic_download"] is False
    assert len(payload["items"]) == 1


def test_result_updates_queue_only_after_validation(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    queue = MissingMediaQueue(database)
    queue.add_from_completeness(_completeness())
    service = MissingMediaHandoffService(queue, database)

    payload = service.create_handoff(
        target_plugin="mediahub.list_export",
    )
    item_id = payload["items"][0]["id"]

    result = service.apply_result(
        {
            "handoff_id": payload["handoff_id"],
            "item_id": item_id,
            "status": "resolved",
            "source_plugin": "mediahub.list_export",
            "note": "In Bibliothek gefunden.",
        }
    )

    assert result["accepted"] is True
    assert queue.get(item_id)["status"] == "resolved"


def test_foreign_item_is_rejected(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    queue = MissingMediaQueue(database)
    service = MissingMediaHandoffService(queue, database)
    payload = service.create_handoff(
        target_plugin="mediahub.list_export",
    )

    try:
        service.apply_result(
            {
                "handoff_id": payload["handoff_id"],
                "item_id": "not-part-of-handoff",
                "status": "resolved",
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Fremder Eintrag wurde akzeptiert.")
