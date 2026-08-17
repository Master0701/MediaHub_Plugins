from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_existing_metadata_panel_exists():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert (
        '"Vorhandene Metadaten"' in text
        or '"Vorhandene / alte Metadaten  (NFO / Datei)"' in text
    )
    assert "self.original_metadata_preview = QTextEdit()" in text
    assert "def _update_original_metadata_preview(" in text

def test_ai_populates_editor_fields_without_writing():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "def _populate_editor_from_ai(" in text
    assert "self._populate_editor_from_ai(result)" in text
    assert "self.series_edit.setText" in text
    assert "self.season_edit.setValue" in text
    assert '"mode": "confirmed_write"' in text

def test_ai_poster_preview_does_not_replace_local_poster():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "def cache_ai_poster(" in text
    assert "def _show_ai_poster_preview(" in text
    assert '"KI-/Online-Poster-Vorschlag' in text
