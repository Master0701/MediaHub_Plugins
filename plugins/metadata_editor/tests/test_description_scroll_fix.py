from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")

def test_full_description_editor_is_hidden_in_main_window():
    assert "self.description_edit = QTextEdit()" in TEXT
    assert "self.description_edit.setVisible(False)" in TEXT

def test_description_dialog_has_vertical_scrollbar():
    assert "def _edit_description_dialog(self):" in TEXT
    assert "editor.setVerticalScrollBarPolicy(" in TEXT
    assert "Qt.ScrollBarPolicy.ScrollBarAsNeeded" in TEXT

def test_description_dialog_cannot_scroll_horizontally():
    assert "editor.setHorizontalScrollBarPolicy(" in TEXT
    assert "Qt.ScrollBarPolicy.ScrollBarAlwaysOff" in TEXT

def test_description_dialog_wraps_inside_editor():
    assert "editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)" in TEXT

def test_release_field_still_exists():
    assert '"Veröffentlichung / Ausstrahlung"' in TEXT
    assert "self.date_edit" in TEXT
