from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_basic_group_exists():
    assert 'QGroupBox("Grunddaten")' in TEXT


def test_description_uses_compact_preview():
    assert "self.description_preview = QLineEdit()" in TEXT
    assert "self.description_preview.setReadOnly(True)" in TEXT
    assert "self.description_edit = QTextEdit()" in TEXT
    assert "self.description_edit.setVisible(False)" in TEXT


def test_description_dialog_model_remains_available():
    assert "def _edit_description_dialog(self):" in TEXT
    assert "self.btn_description_edit = QPushButton(" in TEXT


def test_old_visible_description_editor_is_gone():
    assert "description_row.addWidget(self.description_edit, 1)" not in TEXT


def test_editor_uses_scroll_area():
    assert "editor_scroll = QScrollArea()" in TEXT
    assert "editor_scroll.setWidgetResizable(True)" in TEXT
    assert "editor_scroll.setWidget(editor_group)" in TEXT
    assert "left_layout.addWidget(editor_scroll, 4)" in TEXT
