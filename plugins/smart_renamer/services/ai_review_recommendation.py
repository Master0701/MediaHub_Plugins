from __future__ import annotations

from typing import Any


class AIReviewRecommendationService:
    """Normalize an optional AI rename-review recommendation.

    The result is advisory only. Candidate IDs are accepted only when they
    exist in the supplied review context.
    """

    MEDIA_FIELDS = (
        "media_type",
        "title",
        "year",
        "season",
        "episode",
        "episode_end",
        "episode_title",
        "edition",
        "part",
    )

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            return 0.0

    def normalize(
        self,
        ai_result: dict[str, Any] | None,
        review_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        ai = dict(ai_result or {})
        context = dict(review_context or {})
        candidates = [
            dict(item or {})
            for item in (context.get("candidates") or [])
        ]
        by_id = {
            str(item.get("candidate_id") or ""): item
            for item in candidates
            if str(item.get("candidate_id") or "")
        }

        structured = dict(
            ai.get("structured_recommendation")
            or ai.get("candidate_recommendation")
            or {}
        )

        candidate_id = str(
            structured.get("candidate_id")
            or ai.get("candidate_id")
            or ai.get("recommended_candidate_id")
            or ""
        )
        candidate_valid = bool(candidate_id and candidate_id in by_id)
        candidate = dict(by_id.get(candidate_id) or {})

        fields: dict[str, str] = {}
        for key in self.MEDIA_FIELDS:
            value = (
                structured.get(key)
                if key in structured
                else ai.get(key)
            )
            if value in (None, "") and candidate_valid:
                value = candidate.get(key)
            fields[key] = str(value or "")

        confidence = self._clamp(
            structured.get("confidence")
            or ai.get("confidence")
            or candidate.get("confidence")
            or 0.0
        )
        rationale = str(
            structured.get("rationale")
            or structured.get("reason")
            or ai.get("rationale")
            or ai.get("reason")
            or ""
        )

        recommendation = str(
            structured.get("recommendation")
            or ai.get("recommendation")
            or ""
        )
        suggested_name = str(
            structured.get("suggested_name")
            or ai.get("suggested_name")
            or ""
        )

        warnings = [str(x) for x in (ai.get("warnings") or [])]
        if candidate_id and not candidate_valid:
            warnings.append(
                f"KI-Kandidat '{candidate_id}' ist nicht in den "
                "bereitgestellten Erkennungskandidaten enthalten."
            )

        return {
            "candidate_id": candidate_id if candidate_valid else "",
            "candidate_valid": candidate_valid,
            "candidate": candidate if candidate_valid else {},
            "fields": fields,
            "recommendation": recommendation,
            "suggested_name": suggested_name,
            "confidence": confidence,
            "rationale": rationale,
            "warnings": warnings,
            "advisory_only": True,
            "execution_allowed": False,
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
        }
