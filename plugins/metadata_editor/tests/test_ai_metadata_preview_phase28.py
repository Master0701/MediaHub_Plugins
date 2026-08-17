from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_metadata_editor_consumes_ai_capability():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert 'self._resolve_capability("ai.metadata_review")' in text
    assert 'def ai_metadata_review(' in text

def test_metadata_editor_has_ai_preview_ui():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert 'QPushButton("KI-Metadaten prüfen")' in text
    assert 'self.ai_metadata_preview = QTextEdit()' in text
    assert 'def _review_metadata_with_ai(' in text
    assert 'Nur Vorschau · keine automatische Übernahme.' in text

def test_metadata_write_stays_locked():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert '"mode": "confirmed_write"' in text
    assert 'result["metadata_write_allowed"] = False' in text
