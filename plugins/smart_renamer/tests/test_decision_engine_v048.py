from __future__ import annotations

from pathlib import Path

from services.decision_engine import DecisionEngine
from services.detection_candidates import (
    CandidateSet,
    DetectionCandidate,
)
from services.media_scanner import MediaScanner


def _candidate(
    candidate_id: str,
    confidence: float,
    *,
    media_type: str = "movie",
    title: str = "Film",
    source: str = "local_filename",
):
    return DetectionCandidate(
        candidate_id=candidate_id,
        source=source,
        media_type=media_type,
        title=title,
        confidence=confidence,
    )


def test_clear_high_confidence_candidate_is_selected_for_preview():
    engine = DecisionEngine()
    result = engine.decide(
        CandidateSet(
            candidates=(
                _candidate("one", 0.95),
                _candidate("two", 0.60, title="Andere"),
            )
        )
    )

    assert result.selected_candidate_id == "one"
    assert result.state == "preview_selected"
    assert result.review_required is False
    assert result.confidence >= 0.95
    assert result.to_dict()["automatic_execution"] is False


def test_close_candidates_require_review():
    engine = DecisionEngine()
    result = engine.decide(
        CandidateSet(
            candidates=(
                _candidate("one", 0.90),
                _candidate("two", 0.84, title="Alternative"),
            )
        )
    )

    assert result.review_required is True
    assert result.state == "review_required"
    assert "dicht" in result.reason


def test_unknown_media_type_is_penalized():
    engine = DecisionEngine()
    result = engine.decide(
        CandidateSet(
            candidates=(
                _candidate(
                    "unknown",
                    0.95,
                    media_type="unknown",
                    title="Unklar",
                ),
                _candidate(
                    "movie",
                    0.82,
                    media_type="movie",
                    title="Unklar",
                ),
            )
        )
    )

    assert result.selected_candidate_id == "movie"


def test_preferred_candidate_hint_can_break_close_ranking():
    engine = DecisionEngine()
    result = engine.decide(
        CandidateSet(
            candidates=(
                _candidate("one", 0.88, title="Titel A"),
                _candidate("two", 0.84, title="Titel B"),
            )
        ),
        hints={"preferred_candidate_id": "two"},
    )

    assert result.selected_candidate_id == "two"
    assert any(
        "bevorzugter Kandidat" in signal
        for signal in result.selected.signals
    )


def test_preferred_media_type_is_only_a_bias_not_a_forced_answer():
    engine = DecisionEngine()
    result = engine.decide(
        CandidateSet(
            candidates=(
                _candidate("movie", 0.97, media_type="movie"),
                _candidate(
                    "series",
                    0.70,
                    media_type="series",
                    title="Serie",
                ),
            )
        ),
        hints={"preferred_media_type": "series"},
    )

    assert result.selected_candidate_id == "movie"


def test_no_candidates_is_unresolved():
    result = DecisionEngine().decide(
        CandidateSet(candidates=())
    )

    assert result.state == "unresolved"
    assert result.review_required is True
    assert result.selected_candidate_id == ""


def test_scanner_stores_decision_and_uses_selected_candidate(tmp_path: Path):
    path = tmp_path / "Film 2024.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, skipped = MediaScanner().scan([{"path": str(path)}])

    assert skipped == []
    item = scanned[0]
    decision = item.detection_data["decision"]
    assert decision["selected_candidate_id"]
    assert decision["automatic_execution"] is False
    assert item.detection_data["decision_state"] in {
        "preview_selected",
        "review_required",
    }
    assert item.media_type == "movie"
    assert item.year == "2024"


def test_explicit_metadata_still_overrides_decision(tmp_path: Path):
    path = tmp_path / "Film 2024.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, _ = MediaScanner().scan([
        {
            "path": str(path),
            "metadata": {
                "media_type": "series",
                "titel": "Manuelle Serie",
                "staffel": "08",
                "episode": "04",
            },
        }
    ])

    item = scanned[0]
    assert item.media_type == "series"
    assert item.title == "Manuelle Serie"
    assert item.season == "08"
    assert item.episode == "04"
    assert item.detection_data["decision"]["selected_candidate_id"]


def test_decision_hints_are_optional_and_local_to_item(tmp_path: Path):
    path = tmp_path / "Batman.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, _ = MediaScanner().scan([
        {
            "path": str(path),
            "decision_hints": {
                "preferred_media_type": "movie",
                "preferred_title": "Batman",
            },
        }
    ])

    decision = scanned[0].detection_data["decision"]
    assert decision["selected_candidate_id"]
    assert decision["confidence"] > 0
