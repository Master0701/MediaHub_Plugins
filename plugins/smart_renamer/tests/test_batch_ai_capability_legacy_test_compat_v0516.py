from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_phase2_legacy_exact_capability_marker_remains_present():
    text = (ROOT / "services" / "batch_ai_review_bridge.py").read_text(encoding="utf-8")
    assert 'CAPABILITY="ai.rename_batch_review"' in text

def test_fallback_capability_remains_present():
    text = (ROOT / "services" / "batch_ai_review_bridge.py").read_text(encoding="utf-8")
    assert 'FALLBACK_CAPABILITY="ai.rename_review"' in text
