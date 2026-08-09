from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_review_state_is_initialized_before_build():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")
    init_pos = text.index("self.last_ai_review = None")
    build_pos = text.index("self._build()", init_pos)
    assert init_pos < build_pos

    fusion_pos = text.index("self.last_fusion_result = None")
    evidence_pos = text.index("self.last_evidence_result = None")
    assert fusion_pos < build_pos
    assert evidence_pos < build_pos


def test_preview_formatters_can_read_initialized_state():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")
    assert "def _format_ai_review_detail" in text
    assert "def _format_fusion_detail" in text
    assert "def _format_evidence_detail" in text
    assert "self.last_ai_review = None" in text
    assert "self.last_fusion_result = None" in text
    assert "self.last_evidence_result = None" in text
