from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_preview_actions_are_split_into_two_rows():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    assert "preview_actions_top = QHBoxLayout()" in text
    assert "preview_actions_bottom = QHBoxLayout()" in text
    assert "center_layout.addLayout(preview_actions_top)" in text
    assert "center_layout.addLayout(preview_actions_bottom)" in text

    top_start = text.index("preview_actions_top = QHBoxLayout()")
    top_end = text.index("center_layout.addLayout(preview_actions_top)", top_start)
    top = text[top_start:top_end]

    bottom_start = text.index("preview_actions_bottom = QHBoxLayout()", top_end)
    bottom_end = text.index("center_layout.addLayout(preview_actions_bottom)", bottom_start)
    bottom = text[bottom_start:bottom_end]

    assert 'QPushButton("Auswahl übernehmen")' in top
    assert 'QPushButton("Auswahl ignorieren")' in top
    assert 'QPushButton("Auswahl prüfen")' in top
    assert 'QPushButton("KI prüfen")' in top
    assert 'QPushButton("Als Referenz")' in top

    assert 'QPushButton("KI auf Auswahl")' in bottom
    assert 'QPushButton("Entscheidung vergleichen")' in bottom
    assert 'QPushButton("Belege anzeigen")' in bottom
    assert 'QLabel("0 ausgewählt")' in bottom


def test_two_rows_have_spacing_and_minimum_widths():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    assert "preview_actions_top.setSpacing(10)" in text
    assert "preview_actions_bottom.setSpacing(10)" in text
    assert "self.accept_button.setMinimumWidth(130)" in text
    assert "self.ignore_button.setMinimumWidth(125)" in text
    assert "self.review_button.setMinimumWidth(115)" in text
    assert "self.ai_review_button.setMinimumWidth(95)" in text
    assert "self.ai_reference_button.setMinimumWidth(110)" in text
    assert "self.ai_batch_button.setMinimumWidth(125)" in text
    assert "self.fusion_button.setMinimumWidth(175)" in text
    assert "self.evidence_button.setMinimumWidth(120)" in text
