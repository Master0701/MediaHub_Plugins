import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.semantic_identity import SemanticIdentityEngine


def _candidate(
    confidence=0.95,
    status="confirmed_ready",
    groups=3,
    critical=0,
):
    return {
        "media_type": "movie",
        "title": "Aquaman and the Lost Kingdom",
        "year": 2023,
        "semantic_confidence": confidence,
        "semantic_status": status,
        "evidence_summary": {
            "independent_group_count": groups,
        },
        "contradiction_summary": {
            "critical_count": critical,
        },
        "explainable_decision": {
            "conclusion": "Aquaman erreicht eine hohe semantische Sicherheit.",
            "recommendation": "Die Identität ist bereit für die finale Entscheidung.",
        },
    }


def _result(candidates, gap=0.20):
    return {
        "stage": "explainable_decision",
        "decision_made": False,
        "confidence_gap": gap,
        "candidates": candidates,
    }


def test_confirmed_identity_allows_learning():
    result = SemanticIdentityEngine().finalize(
        _result([_candidate()])
    )

    assert result["decision_made"] is True
    assert result["final_status"] == "confirmed"
    assert result["needs_user_confirmation"] is False
    assert result["allow_learning"] is True
    assert result["identity"]["title"] == "Aquaman and the Lost Kingdom"


def test_close_runner_up_requires_confirmation():
    result = SemanticIdentityEngine().finalize(
        _result(
            [
                _candidate(),
                _candidate(confidence=0.92, status="probable"),
            ],
            gap=0.03,
        )
    )

    assert result["needs_user_confirmation"] is True
    assert result["allow_learning"] is False


def test_critical_conflict_blocks_confirmation():
    result = SemanticIdentityEngine().finalize(
        _result(
            [
                _candidate(
                    confidence=0.98,
                    status="confirmed_ready",
                    groups=4,
                    critical=1,
                )
            ]
        )
    )

    assert result["final_status"] == "candidate"
    assert result["needs_user_confirmation"] is True
    assert result["allow_learning"] is False


def test_probable_candidate_is_not_auto_confirmed():
    result = SemanticIdentityEngine().finalize(
        _result(
            [
                _candidate(
                    confidence=0.86,
                    status="probable",
                    groups=3,
                )
            ]
        )
    )

    assert result["final_status"] == "probable"
    assert result["needs_user_confirmation"] is True
    assert result["allow_learning"] is False


def test_no_candidates_returns_unknown():
    result = SemanticIdentityEngine().finalize(
        _result([], gap=None)
    )

    assert result["final_status"] == "unknown"
    assert result["identity"] is None
    assert result["needs_user_confirmation"] is True
