import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.semantic_identity import IdentityDecisionExplainer


def _candidate(status="probable", critical=0):
    return {
        "title": "Aquaman and the Lost Kingdom",
        "year": 2023,
        "media_type": "movie",
        "semantic_confidence": 0.86,
        "semantic_confidence_percent": 86.0,
        "semantic_status": status,
        "evidence_strength": 0.90,
        "evidence_summary": {
            "independent_group_count": 3,
            "coverage": {
                "missing_groups": ["audio", "subtitle"],
            },
        },
        "evidence": [
            {
                "source": "filename",
                "independent_group": "filename",
                "value": "Aquaman 2",
                "confidence": 0.50,
                "weighted_strength": 0.17,
                "used_for_group_score": True,
                "detail": "Dateiname liefert einen schwachen Titelhinweis.",
            },
            {
                "source": "online",
                "independent_group": "online",
                "value": "Aquaman and the Lost Kingdom",
                "confidence": 0.90,
                "weighted_strength": 0.61,
                "used_for_group_score": True,
                "detail": "Online-Treffer stimmt überein.",
            },
            {
                "source": "visual_ocr",
                "independent_group": "visual_text",
                "value": "AQUAMAN",
                "confidence": 0.82,
                "weighted_strength": 0.49,
                "used_for_group_score": True,
                "detail": "Titelkarte erkannt.",
            },
            {
                "source": "visual_ocr",
                "independent_group": "visual_text",
                "value": "LOST KINGDOM",
                "confidence": 0.70,
                "weighted_strength": 0.41,
                "used_for_group_score": False,
                "detail": "Zusätzlicher OCR-Hinweis.",
            },
        ],
        "contradiction_summary": {
            "critical_count": critical,
            "conflict_count": critical,
            "conflicts": (
                [
                    {
                        "kind": "fingerprint_identity",
                        "severity": "critical",
                        "expected": "Aquaman and the Lost Kingdom",
                        "observed": "The Matrix",
                        "source": "fingerprint",
                        "penalty": 0.34,
                        "detail": "Fingerprint widerspricht dem Kandidaten.",
                    }
                ]
                if critical
                else []
            ),
        },
        "confidence_summary": {
            "status": status,
            "trust_label": "high",
            "limitations": [],
        },
    }


def _result(candidate):
    return {
        "stage": "confidence_calculator",
        "decision_made": False,
        "confidence_gap": 0.22,
        "candidates": [candidate],
    }


def test_explainer_lists_used_supporting_and_missing_evidence():
    result = IdentityDecisionExplainer().explain(
        _result(_candidate())
    )
    explanation = result["best_candidate"]["explainable_decision"]

    assert result["stage"] == "explainable_decision"
    assert result["decision_made"] is False
    assert len(explanation["used_evidence"]) == 3
    assert len(explanation["supporting_evidence"]) == 1
    assert {item["group"] for item in explanation["missing_evidence"]} == {
        "audio",
        "subtitle",
    }


def test_explanation_contains_conclusion_and_recommendation():
    result = IdentityDecisionExplainer().explain(
        _result(_candidate())
    )
    explanation = result["best_candidate"]["explainable_decision"]

    assert "Aquaman" in explanation["conclusion"]
    assert "86.0" in explanation["conclusion"]
    assert explanation["recommendation"]
    assert explanation["final_decision_made"] is False


def test_critical_conflict_is_visible_and_blocks_recommendation():
    result = IdentityDecisionExplainer().explain(
        _result(_candidate(status="candidate", critical=1))
    )
    explanation = result["best_candidate"]["explainable_decision"]

    assert len(explanation["conflicts"]) == 1
    assert explanation["conflicts"][0]["severity"] == "critical"
    assert "Nicht automatisch übernehmen" in explanation["recommendation"]


def test_confirmed_ready_recommendation_points_to_v225():
    result = IdentityDecisionExplainer().explain(
        _result(_candidate(status="confirmed_ready"))
    )
    explanation = result["best_candidate"]["explainable_decision"]

    assert "v2.2.5" in explanation["recommendation"]
