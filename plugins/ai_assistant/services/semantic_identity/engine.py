from __future__ import annotations

from copy import deepcopy
from typing import Any


class SemanticIdentityEngine:
    """Trifft die finale semantische Entscheidung aus allen Vorstufen."""

    @staticmethod
    def _group_count(candidate: dict[str, Any]) -> int:
        return int(
            (
                candidate.get("evidence_summary")
                or {}
            ).get("independent_group_count")
            or 0
        )

    @staticmethod
    def _critical_count(candidate: dict[str, Any]) -> int:
        return int(
            (
                candidate.get("contradiction_summary")
                or {}
            ).get("critical_count")
            or 0
        )

    @staticmethod
    def _status(candidate: dict[str, Any]) -> str:
        semantic_status = str(
            candidate.get("semantic_status") or "candidate"
        )
        confidence = float(
            candidate.get("semantic_confidence") or 0.0
        )
        groups = SemanticIdentityEngine._group_count(candidate)
        critical = SemanticIdentityEngine._critical_count(candidate)

        if critical:
            return "candidate"
        if semantic_status == "confirmed_ready" and confidence >= 0.92 and groups >= 3:
            return "confirmed"
        if semantic_status == "probable":
            return "probable"
        if semantic_status == "possible":
            return "possible"
        return "candidate"

    @staticmethod
    def _needs_user_confirmation(
        final_status: str,
        confidence: float,
        groups: int,
        critical: int,
        confidence_gap: float | None,
    ) -> bool:
        if critical:
            return True
        if final_status != "confirmed":
            return True
        if groups < 3:
            return True
        if confidence < 0.92:
            return True
        if confidence_gap is not None and confidence_gap < 0.12:
            return True
        return False

    @staticmethod
    def _allow_learning(
        final_status: str,
        needs_user_confirmation: bool,
        critical: int,
        confidence_gap: float | None,
    ) -> bool:
        if final_status != "confirmed":
            return False
        if needs_user_confirmation:
            return False
        if critical:
            return False
        if confidence_gap is not None and confidence_gap < 0.12:
            return False
        return True

    @staticmethod
    def _decision_reason(
        candidate: dict[str, Any],
        final_status: str,
        confidence_gap: float | None,
    ) -> str:
        explanation = candidate.get("explainable_decision") or {}
        conclusion = str(explanation.get("conclusion") or "").strip()
        recommendation = str(
            explanation.get("recommendation") or ""
        ).strip()

        pieces = []
        if conclusion:
            pieces.append(conclusion)
        if confidence_gap is not None:
            pieces.append(
                f"Abstand zum zweitbesten Kandidaten: "
                f"{round(confidence_gap * 100, 1)} Prozentpunkte."
            )
        pieces.append(f"Finaler semantischer Status: {final_status}.")
        if recommendation:
            pieces.append(recommendation)
        return " ".join(pieces)

    def finalize(
        self,
        explanation_result: dict[str, Any] | None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(explanation_result or {})
        candidates = [
            deepcopy(item)
            for item in (source.get("candidates") or [])
        ]

        if not candidates:
            return {
                "schema_version": 6,
                "pipeline_version": "2.2.5",
                "stage": "semantic_identity_engine",
                "decision_made": True,
                "final_status": "unknown",
                "identity": None,
                "confidence": 0.0,
                "confidence_percent": 0.0,
                "needs_user_confirmation": True,
                "allow_learning": False,
                "auto_learn_allowed": False,
                "reason": "Es wurde kein verwertbarer Identitätskandidat gefunden.",
                "candidates": [],
                "best_candidate": None,
                "runner_up": None,
            }

        best = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else None
        confidence_gap = source.get("confidence_gap")
        confidence = float(
            best.get("semantic_confidence") or 0.0
        )
        groups = self._group_count(best)
        critical = self._critical_count(best)
        final_status = self._status(best)

        needs_confirmation = self._needs_user_confirmation(
            final_status,
            confidence,
            groups,
            critical,
            confidence_gap,
        )
        allow_learning = self._allow_learning(
            final_status,
            needs_confirmation,
            critical,
            confidence_gap,
        )

        identity = {
            "media_type": best.get("media_type"),
            "title": best.get("title"),
            "year": best.get("year"),
            "season": best.get("season"),
            "episode": best.get("episode"),
            "edition": best.get("edition"),
        }

        best["final_status"] = final_status
        best["needs_user_confirmation"] = needs_confirmation
        best["allow_learning"] = allow_learning
        best["auto_learn_allowed"] = allow_learning
        best["final_reason"] = self._decision_reason(
            best,
            final_status,
            confidence_gap,
        )
        best["stage"] = "semantic_identity_finalized"

        return {
            "schema_version": 6,
            "pipeline_version": "2.2.5",
            "stage": "semantic_identity_engine",
            "decision_made": True,
            "final_status": final_status,
            "identity": identity,
            "confidence": round(confidence, 4),
            "confidence_percent": round(confidence * 100, 1),
            "needs_user_confirmation": needs_confirmation,
            "allow_learning": allow_learning,
            "auto_learn_allowed": allow_learning,
            "reason": best["final_reason"],
            "best_candidate": best,
            "runner_up": runner_up,
            "confidence_gap": confidence_gap,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "safety_policy": {
                "minimum_confirmed_confidence": 0.92,
                "minimum_independent_groups": 3,
                "minimum_confidence_gap": 0.12,
                "critical_conflict_blocks_confirmation": True,
                "learning_requires_confirmed_without_user_confirmation": True,
            },
        }
