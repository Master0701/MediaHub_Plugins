from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_plugin_normalizes_structured_ai_recommendation():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "AIReviewRecommendationService" in text
    assert "self.ai_review_recommendation = AIReviewRecommendationService()" in text
    assert "structured = self.ai_review_recommendation.normalize" in text
    assert 'result["structured_recommendation"] = structured' in text
    assert 'result["recommended_candidate_id"]' in text
    assert '"automatic_apply_allowed": False' in text
    assert '"execution_allowed": False' in text
    assert '"human_confirmation_required": True' in text
