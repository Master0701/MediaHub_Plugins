from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_desktop_gui_displays_ai_comparison():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "AIReviewComparisonService" in text
    assert "self.ai_review_comparison = AIReviewComparisonService()" in text
    assert "def compare_review_recommendation" in text
    assert "self.last_ai_comparison = None" in text
    assert "self.last_ai_comparison = self.plugin.compare_review_recommendation" in text
    assert "def _format_ai_comparison_detail" in text
    assert "self.plugin.ai_review_comparison.format_text(result)" in text
    assert "self.preview_details.setMaximumHeight(280)" in text
