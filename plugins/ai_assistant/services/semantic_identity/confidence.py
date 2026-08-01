from __future__ import annotations

from copy import deepcopy
from typing import Any


class IdentityConfidenceCalculator:
    """Berechnet vorsichtige, erklärbare Vertrauenswerte pro Kandidat."""

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _group_count(candidate: dict[str, Any]) -> int:
        summary = candidate.get("evidence_summary") or {}
        return int(summary.get("independent_group_count") or 0)

    @staticmethod
    def _critical_count(candidate: dict[str, Any]) -> int:
        summary = candidate.get("contradiction_summary") or {}
        return int(summary.get("critical_count") or 0)

    @staticmethod
    def _status(confidence: float, groups: int, critical: int) -> str:
        if critical:
            return "candidate"
        if confidence >= 0.92 and groups >= 3:
            return "confirmed_ready"
        if confidence >= 0.80 and groups >= 2:
            return "probable"
        if confidence >= 0.62:
            return "possible"
        return "candidate"

    @staticmethod
    def _trust_label(confidence: float) -> str:
        if confidence >= 0.92:
            return "very_high"
        if confidence >= 0.80:
            return "high"
        if confidence >= 0.62:
            return "medium"
        if confidence >= 0.40:
            return "low"
        return "very_low"

    @staticmethod
    def _independence_bonus(groups: int) -> float:
        return {
            0: 0.0,
            1: 0.0,
            2: 0.05,
            3: 0.10,
            4: 0.14,
            5: 0.17,
        }.get(groups, 0.20)

    @staticmethod
    def _single_group_cap(groups: int) -> float:
        if groups <= 0:
            return 0.35
        if groups == 1:
            return 0.68
        if groups == 2:
            return 0.88
        return 1.0

    @staticmethod
    def _competition_penalty(
        candidate: dict[str, Any],
        index: int,
        candidates: list[dict[str, Any]],
    ) -> tuple[float, str | None]:
        if len(candidates) < 2 or index > 1:
            return 0.0, None

        first = float(candidates[0].get("evidence_strength") or 0.0)
        second = float(candidates[1].get("evidence_strength") or 0.0)
        gap = abs(first - second)

        if gap < 0.04:
            return 0.16, "Der andere Kandidat an der Spitze ist nahezu gleich stark."
        if gap < 0.08:
            return 0.10, "Der Abstand zum anderen Kandidaten ist klein."
        if gap < 0.14:
            return 0.05, "Der Abstand zum anderen Kandidaten ist noch begrenzt."
        return 0.0, None

    def calculate(
        self,
        contradiction_result: dict[str, Any] | None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(contradiction_result or {})
        raw_candidates = list(source.get("candidates") or [])
        candidates: list[dict[str, Any]] = []

        for index, raw in enumerate(raw_candidates):
            candidate = deepcopy(raw)
            evidence_strength = self._clamp(
                candidate.get("evidence_strength")
            )
            candidate_score = self._clamp(
                candidate.get("candidate_score")
            )
            contradiction_penalty = self._clamp(
                candidate.get("contradiction_penalty")
            )
            groups = self._group_count(candidate)
            critical = self._critical_count(candidate)
            independence_bonus = self._independence_bonus(groups)
            competition_penalty, competition_reason = (
                self._competition_penalty(
                    candidate,
                    index,
                    raw_candidates,
                )
            )

            # Evidence ist maßgeblich; Candidate Score dient nur als schwache
            # strukturelle Zusatzinformation.
            base = (evidence_strength * 0.88) + (candidate_score * 0.12)
            before_cap = (
                base
                + independence_bonus
                - contradiction_penalty
                - competition_penalty
            )
            cap = self._single_group_cap(groups)
            confidence = self._clamp(min(before_cap, cap))

            # Kritischer Konflikt verhindert hohe Einstufungen.
            if critical:
                confidence = min(confidence, 0.49)

            status = self._status(confidence, groups, critical)
            reasons = [
                f"Kombinierte Belegstärke: {round(evidence_strength * 100, 1)} %",
                f"Unabhängige Beleggruppen: {groups}",
            ]
            limitations: list[str] = []

            if independence_bonus:
                reasons.append(
                    f"Unabhängigkeitsbonus: +{round(independence_bonus * 100, 1)} %"
                )
            if contradiction_penalty:
                limitations.append(
                    f"Konfliktabzug: -{round(contradiction_penalty * 100, 1)} %"
                )
            if competition_penalty:
                limitations.append(
                    f"Konkurrenzabzug: -{round(competition_penalty * 100, 1)} %"
                )
            if competition_reason:
                limitations.append(competition_reason)
            if groups <= 1:
                limitations.append(
                    "Nur eine unabhängige Beleggruppe; Vertrauen ist begrenzt."
                )
            if critical:
                limitations.append(
                    "Mindestens ein kritischer Identitätskonflikt verhindert eine hohe Einstufung."
                )

            candidate["confidence_summary"] = {
                "base_evidence_strength": round(evidence_strength, 4),
                "candidate_structure_score": round(candidate_score, 4),
                "independence_bonus": round(independence_bonus, 4),
                "contradiction_penalty": round(
                    contradiction_penalty, 4
                ),
                "competition_penalty": round(competition_penalty, 4),
                "single_group_cap": round(cap, 4),
                "confidence": round(confidence, 4),
                "confidence_percent": round(confidence * 100, 1),
                "status": status,
                "trust_label": self._trust_label(confidence),
                "reasons": reasons,
                "limitations": limitations,
            }
            candidate["semantic_confidence"] = round(confidence, 4)
            candidate["semantic_confidence_percent"] = round(
                confidence * 100,
                1,
            )
            candidate["semantic_status"] = status
            candidate["stage"] = "confidence_calculated"
            candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                float(item.get("semantic_confidence") or 0.0),
                float(item.get("evidence_strength") or 0.0),
                float(item.get("candidate_score") or 0.0),
            ),
            reverse=True,
        )

        best = candidates[0] if candidates else None
        runner_up = candidates[1] if len(candidates) > 1 else None
        gap = (
            round(
                float(best.get("semantic_confidence") or 0.0)
                - float(runner_up.get("semantic_confidence") or 0.0),
                4,
            )
            if best and runner_up
            else None
        )

        return {
            "schema_version": 4,
            "stage": "confidence_calculator",
            "decision_made": False,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "best_candidate": best,
            "runner_up": runner_up,
            "confidence_gap": gap,
            "source_stage": source.get("stage"),
            "calculation_policy": {
                "evidence_weight": 0.88,
                "candidate_structure_weight": 0.12,
                "independence_bonus": True,
                "contradiction_penalty": True,
                "competition_penalty": True,
                "single_group_cap": 0.68,
                "critical_conflict_cap": 0.49,
            },
            "limitations": [
                "v2.2.3 berechnet Vertrauen, trifft aber noch keine endgültige Entscheidung.",
                "Die erklärbare finale Auswahl folgt in v2.2.4.",
                "Die vollständige Semantic Identity Engine folgt in v2.2.5.",
            ],
        }
