from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_new_layout_groups():
    assert 'QGroupBox("Grunddaten")' in TEXT
    assert 'QGroupBox("Seriendaten")' in TEXT
    assert 'QGroupBox("Quelle / Zuordnung")' in TEXT
    assert (
        'QGroupBox("Poster-Vorschau")' in TEXT
        or 'QGroupBox("Poster  (Vorschau)")' in TEXT
    )


def test_source_selection():
    assert '"MediaHub / YouTube"' in TEXT
    assert "def _select_source_category(" in TEXT


def test_staffel_episode_same_row():
    assert "season_episode_row = QHBoxLayout()" in TEXT
    assert 'season_episode_row.addWidget(QLabel("Staffel"))' in TEXT
    assert 'season_episode_row.addWidget(QLabel("Episode"))' in TEXT


def test_description_and_editor_scroll_layout():
    assert "self.description_preview = QLineEdit()" in TEXT
    assert "self.description_preview.setReadOnly(True)" in TEXT
    assert "self.btn_description_edit = QPushButton(" in TEXT
    assert "editor_scroll = QScrollArea()" in TEXT
    assert "editor_scroll.setWidget(editor_group)" in TEXT


def test_phase29_ai_ui_stays_present():
    assert "self.original_metadata_preview" in TEXT
    assert "self.ai_metadata_preview" in TEXT
