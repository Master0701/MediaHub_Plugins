from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_concept_layout_split():
    assert "content_split = QSplitter(Qt.Orientation.Horizontal)" in TEXT
    assert 'QGroupBox("Metadaten bearbeiten  (Entwurf ' in TEXT
    assert 'QGroupBox("Vorhandene / alte Metadaten  (NFO / Datei)")' in TEXT


def test_concept_sidebar():
    assert 'QGroupBox("Poster  (Vorschau)")' in TEXT
    assert 'QGroupBox("KI")' in TEXT
    assert 'self.btn_ai_metadata = QPushButton(' in TEXT


def test_concept_ai_bottom():
    assert 'QGroupBox("KI-Metadaten-Vorschau  (nur Entwurf)")' in TEXT
    assert "self.ai_metadata_preview.setMinimumHeight(120)" in TEXT


def test_source_buttons_stay_available():
    assert 'QPushButton("MediaHub / YouTube")' in TEXT
    assert 'self.btn_folder = QPushButton(' in TEXT


def test_staffel_episode_and_groups_remain_available():
    assert "season_episode_row = QHBoxLayout()" in TEXT
    assert 'QGroupBox("Grunddaten")' in TEXT
    assert 'QGroupBox("Seriendaten")' in TEXT
