import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.missing_media_export import (
    MissingMediaExportService,
)
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


def test_json_payload_is_versioned_and_safe(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_result())
    service = MissingMediaExportService(queue)

    payload = service.build_payload()

    assert payload["producer_version"] == "2.4.2"
    assert payload["count"] == 1
    assert payload["automatic_download"] is False
    assert payload["automatic_search"] is False
    assert payload["automatic_file_change"] is False


def test_csv_export_contains_missing_title(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_result())
    service = MissingMediaExportService(queue)

    csv_text = service.to_csv()

    assert "Aquaman and the Lost Kingdom" in csv_text
    assert "franchise" in csv_text


def test_resolved_items_are_not_exported_by_default(tmp_path):
    queue = MissingMediaQueue(tmp_path / "knowledge.sqlite3")
    queue.add_from_completeness(_result())
    item_id = queue.list()[0]["id"]
    queue.set_status(item_id, "resolved")

    payload = MissingMediaExportService(queue).build_payload()

    assert payload["count"] == 0
