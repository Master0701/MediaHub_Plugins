
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")

def test_concept_layout_split():
    assert "content_split = QSplitter(Qt.Orientation.Horizontal)" in TEXT
    assert 'QGroupBox("Metadaten bearbeiten  (Entwurf – noch nicht gespeichert)")' in TEXT
    assert 'QGroupBox("Vorhandene / alte Metadaten  (NFO / Datei)")' in TEXT

def test_concept_sidebar():
    assert 'QGroupBox("Poster  (Vorschau)")' in TEXT
    assert 'QGroupBox("KI")' in TEXT
    assert 'QPushButton("KI-Metadaten prüfen")' in TEXT

def test_concept_ai_bottom():
    assert 'QGroupBox("KI-Metadaten-Vorschau  (nur Entwurf)")' in TEXT
    assert "self.ai_metadata_preview.setMinimumHeight(220)" in TEXT

def test_source_buttons_stay_available():
    assert 'QPushButton("MediaHub / YouTube")' in TEXT
    assert 'QPushButton("Lokalen Ordner wählen…")' in TEXT

def test_staffel_episode_and_release_layout():
    assert "season_episode_row = QHBoxLayout()" in TEXT
    assert '"Veröffentlichung / Ausstrahlung"' in TEXT
    assert 'QGroupBox("Grunddaten")' in TEXT
    assert 'QGroupBox("Seriendaten")' in TEXT
