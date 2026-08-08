from pathlib import Path
import json

from services.decision_evidence import DecisionEvidenceService


def test_evidence_contains_renamer_source():
    result = DecisionEvidenceService().build({
        "relation_type": "single",
        "confidence": 0.95,
        "title": "Testserie",
    })
    assert result["explainable"] is True
    assert "renamer" in result["sources"]
    assert "metadata" in result["sources"]
    assert result["execution_allowed"] is False


def test_series_structure_is_explained():
    result = DecisionEvidenceService().build({
        "relation_type": "single",
        "confidence": 0.92,
        "season": 2,
        "episode": 3,
    })
    relation_items = [x for x in result["items"] if x["source"] == "relation"]
    assert relation_items
    assert relation_items[0]["value"] == "S02E03"


def test_review_reason_becomes_evidence():
    result = DecisionEvidenceService().build({
        "relation_type": "split_episode",
        "confidence": 0.8,
        "review_reasons": [{
            "code": "split_episode",
            "label": "Geteilte Episode",
            "severity": "review",
            "message": "Bitte prüfen",
        }],
    })
    assert any(x["source"] == "review" for x in result["items"])


def test_ai_conflict_is_visible():
    result = DecisionEvidenceService().build(
        {"relation_type": "single", "confidence": 0.95},
        {
            "available": True,
            "recommendation": "multi_episode",
            "confidence": 0.94,
            "rationale": "KI sieht mehrere Episoden.",
        },
        {
            "decision": "single",
            "agreement": "conflict",
            "confidence": 0.89,
            "reason": "Widerspruch",
        },
    )
    assert result["conflict_count"] >= 1
    assert any(x["source"] == "ai" for x in result["conflicts"])
    assert any(x["source"] == "fusion" for x in result["conflicts"])


def test_ai_agreement_supports_decision():
    result = DecisionEvidenceService().build(
        {"relation_type": "multi_episode", "confidence": 0.9},
        {
            "available": True,
            "recommendation": "multi_episode",
            "confidence": 0.93,
        },
        {
            "decision": "multi_episode",
            "agreement": "agree",
            "confidence": 0.97,
        },
    )
    ai_items = [x for x in result["items"] if x["source"] == "ai" and x["label"] == "KI-Empfehlung"]
    assert ai_items[0]["supports_decision"] is True


def test_web_and_desktop_evidence_controls_present():
    root = Path(__file__).resolve().parents[1]
    plugin = (root / "plugin.py").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "assets" / "js" / "interactive_preview.js").read_text(encoding="utf-8")

    assert '"/smart-renamer/api/decision-evidence"' in plugin
    assert 'QPushButton("Belege anzeigen")' in plugin
    assert 'id="mh-evidence-run"' in html
    assert "runDecisionEvidence" in js


def test_evidence_never_allows_execution():
    result = DecisionEvidenceService().build(
        {"relation_type": "single", "confidence": 0.99},
        {"available": True, "recommendation": "single", "confidence": 0.99},
        {"decision": "single", "agreement": "agree", "confidence": 0.99},
    )
    assert result["execution_allowed"] is False
    assert result["human_confirmation_required"] is True


def test_version_0515():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    assert tuple(int(x) for x in data["version"].split(".")) >= (0, 5, 15)
