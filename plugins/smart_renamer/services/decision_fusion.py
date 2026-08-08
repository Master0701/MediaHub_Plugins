from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class DecisionFusionResult:
    decision: str
    confidence: float
    review_required: bool
    agreement: str
    reason: str
    renamer_confidence: float
    ai_confidence: float
    ai_available: bool
    execution_allowed: bool = False
    human_confirmation_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionFusionService:
    """
    Kombiniert Renamer-Erkennung und optionale KI-Empfehlung.

    Regeln:
    - Ohne KI bleibt die Renamer-Entscheidung bestehen.
    - Übereinstimmung kann die Confidence erhöhen.
    - Widerspruch erzwingt Review.
    - Niedrige Sicherheit erzwingt Review.
    - Niemals Ausführungsfreigabe.
    """

    SAFE_THRESHOLD = 0.90
    REVIEW_THRESHOLD = 0.75

    def fuse(
        self,
        renamer: dict[str, Any],
        ai: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        renamer = dict(renamer or {})
        ai = dict(ai or {})

        renamer_decision = self._normalise_decision(
            renamer.get("decision")
            or renamer.get("relation_type")
            or renamer.get("recommended_action")
            or ""
        )
        renamer_conf = self._clamp(
            renamer.get("confidence")
            or renamer.get("decision_confidence")
            or 0.0
        )
        renamer_review = bool(renamer.get("review_required"))

        ai_available = bool(ai.get("available"))
        ai_decision = self._normalise_decision(
            ai.get("recommendation")
            or ai.get("relation_type")
            or ""
        )
        ai_conf = self._clamp(ai.get("confidence") or 0.0)

        if not ai_available or not ai_decision:
            review_required = (
                renamer_review
                or renamer_conf < self.SAFE_THRESHOLD
                or not renamer_decision
            )
            return DecisionFusionResult(
                decision=renamer_decision or "review",
                confidence=renamer_conf,
                review_required=review_required,
                agreement="no_ai",
                reason=(
                    "Kein KI-Review verfügbar; Renamer-Bewertung bleibt maßgeblich."
                ),
                renamer_confidence=renamer_conf,
                ai_confidence=0.0,
                ai_available=False,
            ).to_dict()

        if renamer_decision and renamer_decision == ai_decision:
            combined = max(renamer_conf, ai_conf)
            combined = min(0.99, combined + 0.04)
            review_required = (
                renamer_review
                or combined < self.SAFE_THRESHOLD
            )
            return DecisionFusionResult(
                decision=renamer_decision,
                confidence=combined,
                review_required=review_required,
                agreement="agree",
                reason=(
                    "Renamer und KI stimmen überein. "
                    "Die Entscheidungssicherheit wurde moderat angehoben."
                ),
                renamer_confidence=renamer_conf,
                ai_confidence=ai_conf,
                ai_available=True,
            ).to_dict()

        # AI and renamer disagree: always manual review.
        confidence = min(max(renamer_conf, ai_conf), 0.89)
        return DecisionFusionResult(
            decision=renamer_decision or ai_decision or "review",
            confidence=confidence,
            review_required=True,
            agreement="conflict",
            reason=(
                "Renamer und KI widersprechen sich. "
                "Der Fall bleibt zwingend auf Bitte prüfen."
            ),
            renamer_confidence=renamer_conf,
            ai_confidence=ai_conf,
            ai_available=True,
        ).to_dict()

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _normalise_decision(value: Any) -> str:
        text = str(value or "").strip().casefold()
        aliases = {
            "multi episode": "multi_episode",
            "multi-episode": "multi_episode",
            "split episode": "split_episode",
            "split-episode": "split_episode",
            "split movie": "split_movie",
            "split-movie": "split_movie",
            "single episode": "single",
            "single": "single",
            "review_name": "review_name",
        }
        return aliases.get(text, text.replace(" ", "_"))
