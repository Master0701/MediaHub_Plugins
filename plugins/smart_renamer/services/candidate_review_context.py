from __future__ import annotations

from typing import Any


class CandidateReviewContextService:
    """Prepare one preview row for optional AI review.

    The payload is advisory only. This service never permits execution.
    """

    MAX_CANDIDATES = 8

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            return 0.0

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = dict(payload or {})
        candidates: list[dict[str, Any]] = []

        for raw in list(source.get("detection_candidates") or [])[: self.MAX_CANDIDATES]:
            item = dict(raw or {})
            candidates.append({
                "candidate_id": str(item.get("candidate_id") or ""),
                "source": str(item.get("source") or ""),
                "media_type": str(item.get("media_type") or "unknown"),
                "title": str(item.get("title") or ""),
                "year": str(item.get("year") or ""),
                "season": str(item.get("season") or ""),
                "episode": str(item.get("episode") or ""),
                "episode_end": str(item.get("episode_end") or ""),
                "episode_title": str(item.get("episode_title") or ""),
                "edition": str(item.get("edition") or ""),
                "part": str(item.get("part") or ""),
                "confidence": self._clamp(item.get("confidence")),
                "confidence_band": str(item.get("confidence_band") or ""),
                "reasons": [str(x) for x in (item.get("reasons") or [])],
            })

        selected_id = str(source.get("selected_candidate_id") or "")
        selected = next(
            (item for item in candidates if item["candidate_id"] == selected_id),
            candidates[0] if candidates else None,
        )

        return {
            "task": "rename_review",
            "review_question": (
                "Bewerte die Erkennungskandidaten für die Vorschau. "
                "Keine Datei verändern und keine Ausführung freigeben."
            ),
            "current_name": str(source.get("original_name") or ""),
            "proposed_name": str(source.get("proposed_name") or ""),
            "source_path": str(source.get("source_path") or ""),
            "renamer": {
                "media_type": str(source.get("media_type") or "unknown"),
                "season": str(source.get("season") or ""),
                "episode": str(source.get("episode") or ""),
                "episode_end": str(source.get("episode_end") or ""),
                "relation_type": str(source.get("relation_type") or "single"),
                "confidence": self._clamp(source.get("confidence")),
                "review_required": bool(source.get("review_required")),
                "decision_state": str(source.get("decision_state") or ""),
                "decision_reason": str(source.get("decision_reason") or ""),
                "decision_confidence": self._clamp(
                    source.get("decision_confidence")
                    or source.get("confidence")
                ),
            },
            "selected_candidate_id": selected_id,
            "selected_candidate": dict(selected or {}),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "constraints": {
                "execution_allowed": False,
                "automatic_rename_allowed": False,
                "human_confirmation_required": True,
                "answer_is_advisory": True,
            },
        }
