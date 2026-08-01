import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.semantic_identity import IdentityConfidenceCalculator


def _candidate(
    title="Aquaman",
    evidence_strength=0.8,
    candidate_score=0.7,
    groups=3,
    penalty=0.0,
    critical=0,
):
    return {
        "title": title,
        "media_type": "movie",
        "evidence_strength": evidence_strength,
        "candidate_score": candidate_score,
        "contradiction_penalty": penalty,
        "evidence_summary": {
            "independent_group_count": groups,
        },
        "contradiction_summary": {
            "critical_count": critical,
        },
    }


def _result(candidates):
    return {
        "stage": "contradiction_detector",
        "decision_made": False,
        "candidates": candidates,
    }


def test_three_strong_independent_groups_reach_confirmed_ready():
    result = IdentityConfidenceCalculator().calculate(
        _result([_candidate(evidence_strength=0.96, candidate_score=0.9)])
    )

    best = result["best_candidate"]

    assert result["stage"] == "confidence_calculator"
    assert result["decision_made"] is False
    assert best["semantic_confidence"] >= 0.92
    assert best["semantic_status"] == "confirmed_ready"


def test_single_group_is_capped():
    result = IdentityConfidenceCalculator().calculate(
        _result(
            [
                _candidate(
                    evidence_strength=0.99,
                    candidate_score=0.99,
                    groups=1,
                )
            ]
        )
    )

    best = result["best_candidate"]

    assert best["semantic_confidence"] <= 0.68
    assert best["semantic_status"] in {"candidate", "possible"}


def test_critical_conflict_caps_confidence():
    result = IdentityConfidenceCalculator().calculate(
        _result(
            [
                _candidate(
                    evidence_strength=0.99,
                    candidate_score=0.99,
                    groups=4,
                    penalty=0.34,
                    critical=1,
                )
            ]
        )
    )

    best = result["best_candidate"]

    assert best["semantic_confidence"] <= 0.49
    assert best["semantic_status"] == "candidate"


def test_close_competing_candidates_reduce_best_confidence():
    result = IdentityConfidenceCalculator().calculate(
        _result(
            [
                _candidate(
                    title="Aquaman",
                    evidence_strength=0.84,
                    candidate_score=0.8,
                    groups=3,
                ),
                _candidate(
                    title="Star Trek",
                    evidence_strength=0.82,
                    candidate_score=0.8,
                    groups=3,
                ),
            ]
        )
    )

    best = result["best_candidate"]
    summary = best["confidence_summary"]

    assert summary["competition_penalty"] >= 0.10
    assert any(
        "Kandidat" in text
        for text in summary["limitations"]
    )


def test_confidence_gap_is_reported():
    result = IdentityConfidenceCalculator().calculate(
        _result(
            [
                _candidate(
                    title="Aquaman",
                    evidence_strength=0.94,
                    candidate_score=0.9,
                    groups=4,
                ),
                _candidate(
                    title="Star Trek",
                    evidence_strength=0.50,
                    candidate_score=0.5,
                    groups=2,
                ),
            ]
        )
    )

    assert result["confidence_gap"] is not None
    assert result["confidence_gap"] > 0.20
