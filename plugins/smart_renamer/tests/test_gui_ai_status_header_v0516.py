from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ai_status_is_in_preview_header():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    header_start = text.index("preview_head = QHBoxLayout()")
    header_end = text.index("center_layout.addLayout(preview_head)", header_start)
    header = text[header_start:header_end]

    assert 'preview_head.addWidget(QLabel("Vorschau"))' in header
    assert 'self.ai_review_status_label = QLabel("KI: wird geprüft …")' in header
    assert "self.ai_review_status_label.setMinimumWidth(180)" in header
    assert "preview_head.addWidget(self.ai_review_status_label)" in header
    assert 'preview_head.addWidget(QLabel("Suche:"))' in header


def test_ai_status_is_not_in_either_action_row():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    top_start = text.index("preview_actions_top = QHBoxLayout()")
    top_end = text.index("center_layout.addLayout(preview_actions_top)", top_start)
    top = text[top_start:top_end]

    bottom_start = text.index("preview_actions_bottom = QHBoxLayout()", top_end)
    bottom_end = text.index("center_layout.addLayout(preview_actions_bottom)", bottom_start)
    bottom = text[bottom_start:bottom_end]

    assert "preview_actions_top.addWidget(self.ai_review_status_label)" not in top
    assert "preview_actions_bottom.addWidget(self.ai_review_status_label)" not in bottom


def test_ai_action_buttons_have_readable_minimum_widths():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    assert "self.ai_review_button.setMinimumWidth(95)" in text
    assert "self.ai_reference_button.setMinimumWidth(110)" in text
    assert "self.ai_batch_button.setMinimumWidth(125)" in text
    assert "self.fusion_button.setMinimumWidth(175)" in text
    assert "self.evidence_button.setMinimumWidth(120)" in text
