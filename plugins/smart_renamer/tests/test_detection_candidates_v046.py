from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from services.detection_candidates import (
    DetectionCandidate,
    DetectionCandidateService,
)
from services.media_detection import DetectionResult
from services.media_scanner import MediaScanner


class FakeOnlineProvider:
    provider_id = "fake_online"

    def candidates_for(
        self,
        path: Path,
        *,
        local_result: DetectionResult,
    ) -> list[DetectionCandidate]:
        return [
            DetectionCandidate(
                candidate_id="fake-online-1",
                source=self.provider_id,
                media_type="movie",
                title="Online Treffer",
                year="2024",
                confidence=0.94,
                reasons=("Simulierter externer Treffer",),
            )
        ]


def test_series_candidate_has_high_confidence_and_no_review(tmp_path: Path):
    path = tmp_path / "Serie S02E03 Titel.mkv"
    path.write_text("x", encoding="utf-8")

    result = DetectionCandidateService().analyze(path)

    assert result.selected is not None
    assert result.selected.media_type == "series"
    assert result.selected.confidence_band == "high"
    assert result.review_required is False


def test_ambiguous_video_requires_review(tmp_path: Path):
    path = tmp_path / "Batman.mkv"
    path.write_text("x", encoding="utf-8")

    result = DetectionCandidateService().analyze(path)

    assert len(result.candidates) >= 2
    assert result.selected is not None
    assert result.selected.title == "Batman"
    assert result.review_required is True
    assert {
        candidate.media_type
        for candidate in result.candidates
    } >= {"movie", "unknown"}


def test_audio_can_offer_audiobook_alternative(tmp_path: Path):
    path = tmp_path / "Titel.mp3"
    path.write_text("x", encoding="utf-8")

    result = DetectionCandidateService().analyze(path)

    assert {item.media_type for item in result.candidates} >= {
        "music",
        "audiobook",
    }
    assert result.review_required is True


def test_external_provider_can_be_added_without_replacing_local(tmp_path: Path):
    path = tmp_path / "Unklar.mkv"
    path.write_text("x", encoding="utf-8")

    service = DetectionCandidateService()
    service.add_provider(FakeOnlineProvider())
    result = service.analyze(path)

    assert result.selected is not None
    assert result.selected.source == "fake_online"
    assert any(
        item.source == "local_filename"
        for item in result.candidates
    )


def test_duplicate_provider_is_rejected():
    service = DetectionCandidateService()

    try:
        service.add_provider(service.providers[0])
    except ValueError as exc:
        assert "bereits vorhanden" in str(exc)
    else:
        raise AssertionError("Doppelter Provider wurde nicht abgewiesen")


def test_scanner_stores_ranked_candidates_and_review_flag(tmp_path: Path):
    path = tmp_path / "Film 2024.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, skipped = MediaScanner().scan([{"path": str(path)}])

    assert skipped == []
    data = scanned[0].detection_data
    assert data["selected_candidate_id"] == "local-primary"
    assert isinstance(data["candidates"], list)
    assert data["candidates"][0]["confidence"] >= data["candidates"][-1]["confidence"]
    assert data["confidence_band"] in {"high", "medium", "low"}
    assert data["selected_source"] == "local_filename"


def test_candidates_do_not_overwrite_explicit_metadata(tmp_path: Path):
    path = tmp_path / "Film 2024.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, _ = MediaScanner().scan([
        {
            "path": str(path),
            "metadata": {
                "media_type": "series",
                "titel": "Manuell",
                "staffel": "05",
                "episode": "09",
            },
        }
    ])

    item = scanned[0]
    assert item.media_type == "series"
    assert item.title == "Manuell"
    assert item.season == "05"
    assert item.episode == "09"
    assert item.detection_data["candidates"][0]["media_type"] == "movie"


def test_candidate_serialization_exposes_reasons_and_band(tmp_path: Path):
    path = tmp_path / "Film 2024 Extended.mkv"
    path.write_text("x", encoding="utf-8")

    payload = DetectionCandidateService().analyze(path).to_dict()

    first = payload["candidates"][0]
    assert first["confidence_band"] in {"high", "medium", "low"}
    assert isinstance(first["reasons"], list)
    assert first["source"] == "local_filename"
