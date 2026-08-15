from services.rename_review_provider import RenameReviewProvider


def test_provider_selects_valid_candidate_and_stays_read_only():
    result = RenameReviewProvider().analyze({
        "proposed_name": "Batman (1989).mkv",
        "selected_candidate_id": "c1",
        "candidates": [{
            "candidate_id": "c1",
            "media_type": "movie",
            "title": "Batman",
            "year": "1989",
            "confidence": 0.91,
            "reasons": ["Lokaler Kandidat"],
        }],
        "renamer": {"media_type": "movie", "confidence": 0.7},
    })
    assert result["candidate_id"] == "c1"
    assert result["structured_recommendation"]["fields"]["title"] == "Batman"
    assert result["structured_recommendation"]["fields"]["year"] == "1989"
    assert result["confidence"] == 0.91
    assert result["execution_allowed"] is False
    assert result["automatic_apply_allowed"] is False
    assert result["human_confirmation_required"] is True


def test_ai_plugin_declares_runtime_capability_statically():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert 'capabilities["ai.rename_review"] = self' in text
    assert "def analyze_rename_review" in text
