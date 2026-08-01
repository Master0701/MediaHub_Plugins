from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_source_field_selection_gui_exists():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "self.source_comparison_id" in text
    assert "self.source_target_entity" in text
    assert "self.source_field_selection" in text
    assert 'QPushButton("Übernahme prüfen")' in text
    assert 'QPushButton("Felder übernehmen")' in text


def test_source_import_preview_is_before_after_and_confirmed():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def preview_source_field_import(self):" in text
    assert '"before": before' in text
    assert '"after": after' in text
    assert '"automatic_import": False' in text
    assert '"requires_confirmation": True' in text


def test_source_import_calls_confirmed_api():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def apply_source_field_import(self):" in text
    assert "self.plugin.confirm_source_fields(" in text
    assert 'note="Über Source-Manager-GUI bestätigt."' in text
