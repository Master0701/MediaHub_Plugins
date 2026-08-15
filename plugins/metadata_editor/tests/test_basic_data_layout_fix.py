from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")

def test_basic_group_uses_vertical_layout():
    assert 'basic_group = QGroupBox("Grunddaten")' in TEXT
    assert "basic_layout = QVBoxLayout(basic_group)" in TEXT

def test_description_has_own_row():
    assert "description_row = QHBoxLayout()" in TEXT
    assert 'description_label = QLabel("Beschreibung")' in TEXT
    assert "description_row.addWidget(self.description_preview, 1)" in TEXT
    assert "description_row.addWidget(self.btn_description_edit)" in TEXT

def test_release_row_is_separate_from_description():
    assert "date_year_row = QHBoxLayout()" in TEXT
    assert 'release_label = QLabel("Veröffentlichung / Ausstrahlung")' in TEXT
    assert "basic_layout.addLayout(date_year_row)" in TEXT

def test_description_is_compact_dialog_model():
    assert "self.description_preview = QLineEdit()" in TEXT
    assert "self.description_edit.setVisible(False)" in TEXT
    assert "def _edit_description_dialog(self):" in TEXT

def test_old_visible_textedit_row_is_gone():
    assert "description_row.addWidget(self.description_edit, 1)" not in TEXT
