from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from mediahub_smart_renamer_runtime.services.media_detection import DetectionResult, MediaDetector


CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.65


@dataclass(frozen=True, slots=True)
class DetectionCandidate:
    candidate_id: str
    source: str
    media_type: str
    title: str
    year: str = ""
    season: str = ""
    episode: str = ""
    episode_end: str = ""
    episode_title: str = ""
    edition: str = ""
    part: str = ""
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_band(self) -> str:
        if self.confidence >= CONFIDENCE_HIGH:
            return "high"
        if self.confidence >= CONFIDENCE_MEDIUM:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "media_type": self.media_type,
            "title": self.title,
            "year": self.year,
            "season": self.season,
            "episode": self.episode,
            "episode_end": self.episode_end,
            "episode_title": self.episode_title,
            "edition": self.edition,
            "part": self.part,
            "confidence": round(float(self.confidence), 4),
            "confidence_band": self.confidence_band,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CandidateSet:
    candidates: tuple[DetectionCandidate, ...]
    selected_candidate_id: str = ""
    review_required: bool = False

    @property
    def selected(self) -> DetectionCandidate | None:
        for candidate in self.candidates:
            if candidate.candidate_id == self.selected_candidate_id:
                return candidate
        return self.candidates[0] if self.candidates else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "review_required": self.review_required,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@runtime_checkable
class DetectionCandidateProvider(Protocol):
    """Vertrag für spätere KI-/Online-/Datenbank-Kandidatenquellen."""

    provider_id: str

    def candidates_for(
        self,
        path: Path,
        *,
        local_result: DetectionResult,
    ) -> list[DetectionCandidate]:
        ...


class LocalDetectionCandidateProvider:
    provider_id = "local_filename"

    def __init__(self, detector: MediaDetector | None = None) -> None:
        self.detector = detector or MediaDetector()

    def candidates_for(
        self,
        path: Path,
        *,
        local_result: DetectionResult,
    ) -> list[DetectionCandidate]:
        path = Path(path)
        candidates: list[DetectionCandidate] = []

        primary = self._from_result(
            local_result,
            candidate_id="local-primary",
            reasons=self._reasons_for(local_result, primary=True),
        )
        candidates.append(primary)

        raw_title = self.detector._normalize(path.stem)
        if raw_title and raw_title.casefold() != primary.title.casefold():
            candidates.append(
                DetectionCandidate(
                    candidate_id="local-raw-name",
                    source=self.provider_id,
                    media_type=local_result.media_type,
                    title=raw_title,
                    year=local_result.year,
                    season=local_result.season,
                    episode=local_result.episode,
                    episode_end=local_result.episode_end,
                    episode_title=local_result.episode_title,
                    edition=local_result.edition,
                    part=local_result.part,
                    confidence=max(0.05, local_result.confidence - 0.22),
                    reasons=(
                        "Unbereinigter Dateiname als sichere Vergleichsvariante",
                    ),
                    metadata={"fallback": True},
                )
            )

        alternative = self._ambiguous_type_candidate(path, local_result)
        if alternative is not None:
            candidates.append(alternative)

        return candidates

    def _from_result(
        self,
        result: DetectionResult,
        *,
        candidate_id: str,
        reasons: tuple[str, ...],
    ) -> DetectionCandidate:
        return DetectionCandidate(
            candidate_id=candidate_id,
            source=self.provider_id,
            media_type=result.media_type,
            title=result.title,
            year=result.year,
            season=result.season,
            episode=result.episode,
            episode_end=result.episode_end,
            episode_title=result.episode_title,
            edition=result.edition,
            part=result.part,
            confidence=result.confidence,
            reasons=reasons,
            metadata={"evidence": list(result.evidence), **dict(result.extra)},
        )

    @staticmethod
    def _reasons_for(
        result: DetectionResult,
        *,
        primary: bool,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if primary:
            reasons.append("Beste lokale Dateinamenanalyse")
        for evidence in result.evidence:
            if evidence == "series_pattern":
                reasons.append("Eindeutiges Serienmuster erkannt")
            elif evidence.startswith("season:"):
                reasons.append("Staffelnummer erkannt")
            elif evidence.startswith("episode:"):
                reasons.append("Episodennummer erkannt")
            elif evidence.startswith("year:"):
                reasons.append("Jahreszahl erkannt")
            elif evidence.startswith("video_extension:"):
                reasons.append("Videoformat erkannt")
            elif evidence.startswith("audio_extension:"):
                reasons.append("Audioformat erkannt")
            elif evidence.startswith("audiobook_extension:"):
                reasons.append("Eindeutiges Hörbuchformat erkannt")
            elif evidence == "audiobook_hint":
                reasons.append("Hörbuch-/Kapitelhinweis erkannt")
            elif evidence == "numbered_audio_track":
                reasons.append("Nummerierter Audiotrack erkannt")
            elif evidence.startswith("edition:"):
                reasons.append("Schnittfassung/Edition erkannt")
        return tuple(dict.fromkeys(reasons))

    def _ambiguous_type_candidate(
        self,
        path: Path,
        result: DetectionResult,
    ) -> DetectionCandidate | None:
        suffix = path.suffix.casefold()

        if result.media_type == "movie" and not result.year:
            return DetectionCandidate(
                candidate_id="local-video-unknown",
                source=self.provider_id,
                media_type="unknown",
                title=result.title,
                edition=result.edition,
                confidence=max(0.05, result.confidence - 0.18),
                reasons=(
                    "Video ohne Jahr oder Serienmuster kann lokal nicht sicher zugeordnet werden",
                ),
                metadata={"alternative_type": True},
            )

        if result.media_type == "music" and suffix in {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}:
            return DetectionCandidate(
                candidate_id="local-audio-audiobook",
                source=self.provider_id,
                media_type="audiobook",
                title=result.title,
                confidence=max(0.05, result.confidence - 0.25),
                reasons=(
                    "Audioformat kann ohne weitere Metadaten auch zu einem Hörbuch gehören",
                ),
                metadata={"alternative_type": True},
            )

        return None


class DetectionCandidateService:
    """
    Führt Kandidatenquellen zusammen.

    In v0.4.6 wird nur die lokale Quelle mitgeliefert. KI, Online-Datenbanken,
    MediaHub-Datenbank oder AI-Node können später als weitere Provider
    registriert werden, ohne die lokale Erkennung zu ersetzen.
    """

    def __init__(
        self,
        detector: MediaDetector | None = None,
        providers: list[DetectionCandidateProvider] | None = None,
    ) -> None:
        self.detector = detector or MediaDetector()
        self.providers: list[DetectionCandidateProvider] = (
            list(providers)
            if providers is not None
            else [LocalDetectionCandidateProvider(self.detector)]
        )

    def add_provider(self, provider: DetectionCandidateProvider) -> None:
        if any(
            existing.provider_id == provider.provider_id
            for existing in self.providers
        ):
            raise ValueError(
                f"Kandidatenprovider bereits vorhanden: {provider.provider_id}"
            )
        self.providers.append(provider)

    def analyze(self, path: Path) -> CandidateSet:
        path = Path(path)
        local_result = self.detector.detect(path)

        collected: list[DetectionCandidate] = []
        for provider in self.providers:
            collected.extend(
                provider.candidates_for(
                    path,
                    local_result=local_result,
                )
            )

        ranked = self._rank_and_deduplicate(collected)
        selected_id = ranked[0].candidate_id if ranked else ""
        review_required = self._needs_review(ranked)

        return CandidateSet(
            candidates=tuple(ranked),
            selected_candidate_id=selected_id,
            review_required=review_required,
        )

    @staticmethod
    def _rank_and_deduplicate(
        candidates: list[DetectionCandidate],
    ) -> list[DetectionCandidate]:
        deduplicated: dict[
            tuple[str, str, str, str, str, str, str],
            DetectionCandidate,
        ] = {}

        for candidate in candidates:
            key = (
                candidate.media_type.casefold(),
                candidate.title.casefold(),
                candidate.year,
                candidate.season,
                candidate.episode,
                candidate.episode_end,
                candidate.episode_title.casefold(),
                candidate.edition.casefold(),
                candidate.part,
            )
            previous = deduplicated.get(key)
            if previous is None or candidate.confidence > previous.confidence:
                deduplicated[key] = candidate

        return sorted(
            deduplicated.values(),
            key=lambda item: (
                -float(item.confidence),
                item.source,
                item.candidate_id,
            ),
        )

    @staticmethod
    def _needs_review(
        candidates: list[DetectionCandidate],
    ) -> bool:
        if not candidates:
            return True

        best = candidates[0]
        if best.confidence < CONFIDENCE_HIGH:
            return True

        if len(candidates) >= 2:
            gap = best.confidence - candidates[1].confidence
            if gap < 0.12:
                return True

        return False
