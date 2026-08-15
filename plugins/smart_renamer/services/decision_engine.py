from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from mediahub_smart_renamer_runtime.services.detection_candidates import CandidateSet, DetectionCandidate


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Konservative Auswahlregeln für die Vorschau, niemals für Auto-Rename."""

    accept_score: float = 0.85
    minimum_gap: float = 0.12
    unknown_penalty: float = 0.20
    source_weights: Mapping[str, float] = field(
        default_factory=lambda: {
            "local_filename": 0.00,
            "mediahub_database": 0.06,
            "metadata_editor": 0.05,
            "mediahub_ai": 0.04,
            "ai_node": 0.04,
            "online": 0.03,
        }
    )


@dataclass(frozen=True, slots=True)
class RankedDecisionCandidate:
    candidate_id: str
    source: str
    media_type: str
    title: str
    base_confidence: float
    decision_score: float
    signals: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "media_type": self.media_type,
            "title": self.title,
            "base_confidence": round(self.base_confidence, 4),
            "decision_score": round(self.decision_score, 4),
            "signals": list(self.signals),
        }


@dataclass(frozen=True, slots=True)
class DecisionResult:
    selected_candidate_id: str
    state: str
    confidence: float
    review_required: bool
    reason: str
    ranked: tuple[RankedDecisionCandidate, ...] = ()

    @property
    def selected(self) -> RankedDecisionCandidate | None:
        for item in self.ranked:
            if item.candidate_id == self.selected_candidate_id:
                return item
        return self.ranked[0] if self.ranked else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "state": self.state,
            "confidence": round(self.confidence, 4),
            "review_required": self.review_required,
            "reason": self.reason,
            "ranked": [item.to_dict() for item in self.ranked],
            "automatic_execution": False,
        }


class DecisionEngine:
    """
    Zentrale Entscheidungsschicht innerhalb des Smart Renamers.

    Sie entscheidet nur, welcher Kandidat in der VORSCHAU bevorzugt wird.
    Sie darf niemals eine Datei automatisch umbenennen.

    Externe Quellen können später Kandidaten liefern. Der DecisionEngine ist
    deren Herkunft egal; er bewertet nur deklarierte Kandidaten und optionale
    Entscheidungshinweise.
    """

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self.policy = policy or DecisionPolicy()

    def decide(
        self,
        candidate_set: CandidateSet,
        *,
        hints: Mapping[str, Any] | None = None,
    ) -> DecisionResult:
        hints = dict(hints or {})

        if not candidate_set.candidates:
            return DecisionResult(
                selected_candidate_id="",
                state="unresolved",
                confidence=0.0,
                review_required=True,
                reason="Keine Erkennungskandidaten vorhanden.",
                ranked=(),
            )

        ranked = tuple(
            sorted(
                (
                    self._score_candidate(candidate, hints=hints)
                    for candidate in candidate_set.candidates
                ),
                key=lambda item: (
                    -item.decision_score,
                    -item.base_confidence,
                    item.source,
                    item.candidate_id,
                ),
            )
        )

        best = ranked[0]
        second_score = ranked[1].decision_score if len(ranked) > 1 else 0.0
        gap = best.decision_score - second_score

        review_reasons: list[str] = []
        if best.media_type == "unknown":
            review_reasons.append("Bester Kandidat hat unbekannten Medientyp")
        if best.decision_score < self.policy.accept_score:
            review_reasons.append(
                "Entscheidungsscore liegt unter der sicheren Schwelle"
            )
        if len(ranked) > 1 and gap < self.policy.minimum_gap:
            review_reasons.append(
                "Die besten Kandidaten liegen zu dicht beieinander"
            )
        if candidate_set.review_required:
            review_reasons.append(
                "Kandidatenerkennung fordert bereits manuelle Prüfung"
            )

        review_required = bool(review_reasons)
        state = "review_required" if review_required else "preview_selected"
        reason = (
            "; ".join(dict.fromkeys(review_reasons))
            if review_required
            else "Bester Kandidat ist für die Vorschau ausreichend eindeutig."
        )

        return DecisionResult(
            selected_candidate_id=best.candidate_id,
            state=state,
            confidence=best.decision_score,
            review_required=review_required,
            reason=reason,
            ranked=ranked,
        )

    def _score_candidate(
        self,
        candidate: DetectionCandidate,
        *,
        hints: Mapping[str, Any],
    ) -> RankedDecisionCandidate:
        score = float(candidate.confidence)
        signals: list[str] = []

        source_bonus = float(
            self.policy.source_weights.get(candidate.source, 0.0)
        )
        if source_bonus:
            score += source_bonus
            signals.append(
                f"Quellengewicht {candidate.source}: {source_bonus:+.2f}"
            )

        if candidate.media_type == "unknown":
            score -= self.policy.unknown_penalty
            signals.append(
                f"Unbekannter Medientyp: -{self.policy.unknown_penalty:.2f}"
            )

        preferred_id = str(hints.get("preferred_candidate_id") or "")
        if preferred_id and candidate.candidate_id == preferred_id:
            score += 0.08
            signals.append("Explizit bevorzugter Kandidat: +0.08")

        preferred_type = str(hints.get("preferred_media_type") or "")
        if (
            preferred_type
            and candidate.media_type.casefold() == preferred_type.casefold()
        ):
            score += 0.05
            signals.append("Bevorzugter Medientyp: +0.05")

        preferred_title = str(hints.get("preferred_title") or "").strip()
        if (
            preferred_title
            and candidate.title.strip().casefold() == preferred_title.casefold()
        ):
            score += 0.07
            signals.append("Bestätigter Titel stimmt überein: +0.07")

        score = max(0.0, min(1.0, score))

        return RankedDecisionCandidate(
            candidate_id=candidate.candidate_id,
            source=candidate.source,
            media_type=candidate.media_type,
            title=candidate.title,
            base_confidence=float(candidate.confidence),
            decision_score=score,
            signals=tuple(signals),
        )
