from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_description_uses_compact_preview():
    assert "self.description_preview = QLineEdit()" in TEXT
    assert "self.description_preview.setReadOnly(True)" in TEXT
    assert "self.btn_description_edit = QPushButton(" in TEXT


def test_hidden_full_description_field_remains_data_source():
    assert "self.description_edit = QTextEdit()" in TEXT
    assert "self.description_edit.setVisible(False)" in TEXT
    assert '"description": self.description_edit.toPlainText().strip()' in TEXT


def test_description_dialog_exists():
    assert "def _edit_description_dialog(self):" in TEXT
    assert 'dialog.setWindowTitle("Beschreibung bearbeiten")' in TEXT
    assert "QDialogButtonBox.StandardButton.Save" in TEXT
    assert "QDialogButtonBox.StandardButton.Cancel" in TEXT


def test_preview_is_synced_from_file_and_ai():
    assert "def _sync_description_preview(self):" in TEXT
    assert TEXT.count("self._sync_description_preview()") >= 3


def test_editor_scroll_area_keeps_fields_accessible():
    assert "editor_scroll = QScrollArea()" in TEXT
    assert "editor_scroll.setVerticalScrollBarPolicy(" in TEXT
    assert "Qt.ScrollBarPolicy.ScrollBarAsNeeded" in TEXT
