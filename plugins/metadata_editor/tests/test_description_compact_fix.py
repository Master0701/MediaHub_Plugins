from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")

def test_description_is_compact():
    assert "self.description_preview = QLineEdit()" in TEXT
    assert "self.description_preview.setReadOnly(True)" in TEXT
    assert 'QPushButton("Beschreibung bearbeiten…")' in TEXT

def test_full_description_stays_available():
    assert "self.description_edit = QTextEdit()" in TEXT
    assert "self.description_edit.setVisible(False)" in TEXT

def test_release_field_still_exists():
    assert '"Veröffentlichung / Ausstrahlung"' in TEXT
