from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_plugin_wires_candidate_context_into_ai_review():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "CandidateReviewContextService" in text
    assert "self.candidate_review_context = CandidateReviewContextService()" in text
    assert "review_context = self.candidate_review_context.build" in text
    assert "self.ai_review_bridge.analyze(review_context)" in text
    assert 'result["review_context_enriched"] = True' in text
    assert 'result["execution_allowed"] = False' in text
    assert 'result["human_confirmation_required"] = True' in text
