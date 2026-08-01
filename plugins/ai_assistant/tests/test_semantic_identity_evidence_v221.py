import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.semantic_identity import IdentityEvidenceCollector


def _candidate(evidence):
    return {
        "schema_version": 1,
        "stage": "candidate_builder",
        "decision_made": False,
        "candidate_count": 1,
        "sources_considered": ["filename", "online", "fingerprint"],
        "candidates": [
            {
                "media_type": "movie",
                "title": "Aquaman and the Lost Kingdom",
                "year": 2023,
                "candidate_score": 0.75,
                "source_count": len(
                    {item["independent_group"] for item in evidence}
                ),
                "evidence": evidence,
            }
        ],
    }


def test_collector_combines_independent_groups():
    result = IdentityEvidenceCollector().collect(
        _candidate(
            [
                {
                    "source": "filename",
                    "value": "Aquaman 2",
                    "confidence": 0.40,
                    "independent_group": "filename",
                },
                {
                    "source": "online",
                    "value": "Aquaman and the Lost Kingdom",
                    "confidence": 0.88,
                    "independent_group": "online",
                },
                {
                    "source": "fingerprint",
                    "value": "Aquaman and the Lost Kingdom",
                    "confidence": 0.99,
                    "independent_group": "fingerprint",
                },
            ]
        )
    )

    best = result["best_candidate"]
    summary = best["evidence_summary"]

    assert result["stage"] == "evidence_collector"
    assert result["decision_made"] is False
    assert summary["independent_group_count"] == 3
    assert best["evidence_strength"] > 0.90


def test_duplicate_same_evidence_is_removed():
    duplicate = {
        "source": "visual_ocr",
        "value": "STAR TREK",
        "confidence": 0.82,
        "independent_group": "visual_text",
    }
    result = IdentityEvidenceCollector().collect(
        _candidate([duplicate, dict(duplicate)])
    )

    summary = result["best_candidate"]["evidence_summary"]

    assert summary["raw_evidence_count"] == 2
    assert summary["unique_evidence_count"] == 1
    assert summary["duplicate_evidence_count"] == 1


def test_same_group_uses_only_strongest_for_combination():
    result = IdentityEvidenceCollector().collect(
        _candidate(
            [
                {
                    "source": "visual_ocr",
                    "value": "AQUAMAN",
                    "confidence": 0.80,
                    "independent_group": "visual_text",
                },
                {
                    "source": "visual_ocr",
                    "value": "LOST KINGDOM",
                    "confidence": 0.70,
                    "independent_group": "visual_text",
                },
            ]
        )
    )

    best = result["best_candidate"]
    groups = best["evidence_summary"]["groups"]

    assert len(groups) == 1
    assert groups[0]["evidence_count"] == 2
    assert sum(
        bool(item["used_for_group_score"])
        for item in best["evidence"]
    ) == 1
    assert best["evidence_strength"] < 0.50


def test_coverage_lists_missing_evidence_groups():
    result = IdentityEvidenceCollector().collect(
        _candidate(
            [
                {
                    "source": "filename",
                    "value": "Aquaman",
                    "confidence": 0.40,
                    "independent_group": "filename",
                }
            ]
        )
    )

    coverage = result["best_candidate"]["evidence_summary"]["coverage"]

    assert "filename" in coverage["present_groups"]
    assert "fingerprint" in coverage["missing_groups"]
    assert "knowledge" in coverage["missing_groups"]
