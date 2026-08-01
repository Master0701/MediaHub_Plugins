from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_result_import_api_supports_single_and_multiple_results():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def import_missing_media_handoff_results(self, payload):" in text
    assert 'payload.get("results")' in text
    assert '"imported_count": len(imported)' in text
    assert '"error_count": len(errors)' in text


def test_result_import_gui_exists():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'QPushButton("Plugin-Rückmeldung importieren")' in text
    assert "def import_missing_media_handoff_results(self):" in text
    assert "getOpenFileName(" in text


def test_missing_media_block_status_is_visible_and_safe():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'QPushButton("Fehlende-Medien-Status")' in text
    assert "def show_missing_media_block_status(self):" in text
    assert '"automatic_download": False' in text
    assert '"automatic_search": False' in text
    assert '"automatic_file_change": False' in text
