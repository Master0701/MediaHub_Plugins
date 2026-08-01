import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.source_manager_v2 import SourceManagerV2


def test_default_sources_exist(tmp_path):
    manager = SourceManagerV2(tmp_path / "knowledge.sqlite3")
    ids = {item["id"] for item in manager.list_sources()}

    assert {"tmdb", "tvdb", "wikidata", "wikipedia", "local_cache"} <= ids


def test_custom_url_source_is_persistent(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    manager = SourceManagerV2(database)
    source = manager.add_custom_source(
        name="Test-Wiki",
        url="https://example.com/wiki",
        category="chronology",
        trust=0.82,
        priority=55,
    )

    reopened = SourceManagerV2(database)
    loaded = reopened.get_source(source["id"])

    assert loaded["name"] == "Test-Wiki"
    assert loaded["category"] == "chronology"
    assert loaded["trust"] == 0.82


def test_scan_is_preview_only(tmp_path):
    manager = SourceManagerV2(tmp_path / "knowledge.sqlite3")
    source = manager.add_custom_source(
        name="Test",
        url="https://example.com",
    )

    preview = manager.create_scan_preview(source["id"])

    assert preview["status"] == "preview_only"
    assert preview["automatic_import"] is False
    assert preview["requires_confirmation"] is True
    assert preview["network_execution_started"] is False


def test_invalid_url_is_rejected(tmp_path):
    manager = SourceManagerV2(tmp_path / "knowledge.sqlite3")

    try:
        manager.add_custom_source(
            name="Ungültig",
            url="not-a-url",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Ungültige URL wurde akzeptiert.")
