from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")

def test_dialog_imports_layout_locally():
    assert "QVBoxLayout," in TEXT

def test_dialog_opens_description_editor():
    assert 'dialog.setWindowTitle("Beschreibung bearbeiten")' in TEXT
    assert "editor = QTextEdit(dialog)" in TEXT

def test_dialog_has_scrollbar_and_wrap():
    assert "Qt.ScrollBarPolicy.ScrollBarAsNeeded" in TEXT
    assert "QTextEdit.LineWrapMode.WidgetWidth" in TEXT

def test_dialog_has_apply_and_cancel():
    assert "QDialogButtonBox.StandardButton.Save" in TEXT
    assert 'save_button.setText("Übernehmen")' in TEXT
    assert 'cancel_button.setText("Abbrechen")' in TEXT

def test_accept_updates_preview():
    assert "self.description_edit.setPlainText(editor.toPlainText())" in TEXT
    assert "self._sync_description_preview()" in TEXT
