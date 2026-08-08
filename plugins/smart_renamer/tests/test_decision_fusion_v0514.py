from pathlib import Path
import json

from services.decision_fusion import DecisionFusionService


def test_no_ai_keeps_renamer_and_can_require_review():
    result = DecisionFusionService().fuse({
        "relation_type": "single",
        "confidence": 0.95,
        "review_required": False,
    })
    assert result["agreement"] == "no_ai"
    assert result["decision"] == "single"
    assert result["review_required"] is False
    assert result["execution_allowed"] is False


def test_agreement_moderately_increases_confidence():
    result = DecisionFusionService().fuse(
        {"relation_type": "multi_episode", "confidence": 0.86, "review_required": False},
        {"available": True, "recommendation": "multi_episode", "confidence": 0.91},
    )
    assert result["agreement"] == "agree"
    assert result["confidence"] > 0.91
    assert result["confidence"] <= 0.99
    assert result["execution_allowed"] is False


def test_conflict_forces_review():
    result = DecisionFusionService().fuse(
        {"relation_type": "single", "confidence": 0.97, "review_required": False},
        {"available": True, "recommendation": "multi_episode", "confidence": 0.96},
    )
    assert result["agreement"] == "conflict"
    assert result["review_required"] is True
    assert result["confidence"] <= 0.89
    assert "widersprechen" in result["reason"]


def test_existing_renamer_review_is_never_silently_cleared():
    result = DecisionFusionService().fuse(
        {"relation_type": "split_episode", "confidence": 0.95, "review_required": True},
        {"available": True, "recommendation": "split_episode", "confidence": 0.96},
    )
    assert result["agreement"] == "agree"
    assert result["review_required"] is True


def test_low_confidence_without_ai_stays_review():
    result = DecisionFusionService().fuse({
        "relation_type": "single",
        "confidence": 0.70,
        "review_required": False,
    })
    assert result["review_required"] is True


def test_web_and_desktop_fusion_controls_present():
    root = Path(__file__).resolve().parents[1]
    plugin = (root / "plugin.py").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "assets" / "js" / "interactive_preview.js").read_text(encoding="utf-8")

    assert '"/smart-renamer/api/decision-fusion"' in plugin
    assert 'QPushButton("Entscheidung vergleichen")' in plugin
    assert 'id="mh-fusion-run"' in html
    assert "runDecisionFusion" in js


def test_version_0514():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    assert tuple(int(x) for x in data["version"].split(".")) >= (0, 5, 14)
