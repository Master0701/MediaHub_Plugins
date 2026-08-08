from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class ReviewPriority:
    level: str
    score: int
    label: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReviewPriorityService:
    """Priorisiert Review-Fälle, ohne Entscheidungen oder Dateien zu verändern."""

    RELATION_WEIGHTS = {
        "split_movie": 28,
        "split_episode": 26,
        "multi_episode": 24,
        "multi_part": 20,
        "unknown_relation": 18,
    }

    def classify(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row or {})
        score = 0
        reasons: list[str] = []

        if self._is_conflict(row):
            score += 50
            reasons.append("Widerspruch/Konflikt erkannt")

        relation = str(row.get("relation_type") or "single")
        relation_weight = self.RELATION_WEIGHTS.get(relation, 0)
        if relation_weight:
            score += relation_weight
            reasons.append(f"Relation: {relation}")

        if row.get("review_required") or row.get("human_review_required"):
            score += 18
            reasons.append("Manuelle Prüfung erforderlich")

        confidence = self._confidence(row)
        if confidence < 0.60:
            score += 22
            reasons.append("Sehr niedrige Confidence")
        elif confidence < 0.75:
            score += 14
            reasons.append("Niedrige Confidence")
        elif confidence < 0.90:
            score += 6
            reasons.append("Mittlere Confidence")

        review_reasons = list(row.get("review_reasons") or [])
        if review_reasons:
            score += min(12, len(review_reasons) * 3)
            reasons.append(f"{len(review_reasons)} Review-Grund/-Gründe")

        if row.get("blocked") or row.get("highest_severity") == "blocking":
            score += 45
            reasons.append("Blockierender Fall")

        if score >= 70:
            level, label = "critical", "Sofort prüfen"
        elif score >= 45:
            level, label = "high", "Hohe Priorität"
        elif score >= 20:
            level, label = "medium", "Prüfen"
        else:
            level, label = "low", "Niedrige Priorität"

        return ReviewPriority(
            level=level,
            score=min(score, 100),
            label=label,
            reason="; ".join(reasons) or "Kein besonderer Review-Grund",
        ).to_dict()

    def enrich_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched = []
        for row in rows or []:
            item = dict(row or {})
            priority = self.classify(item)
            item["review_priority"] = priority
            item["priority_level"] = priority["level"]
            item["priority_score"] = priority["score"]
            item["priority_label"] = priority["label"]
            enriched.append(item)
        return sorted(
            enriched,
            key=lambda item: (
                -int(item.get("priority_score") or 0),
                str(item.get("original_name") or item.get("current_name") or "").casefold(),
            ),
        )

    @staticmethod
    def summary(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for row in rows or []:
            level = str(row.get("priority_level") or "low")
            if level in counts:
                counts[level] += 1
        counts["total"] = len(rows or [])
        return counts

    @staticmethod
    def _confidence(row: dict[str, Any]) -> float:
        try:
            return max(0.0, min(1.0, float(
                row.get("confidence")
                or row.get("decision_confidence")
                or 0.0
            )))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_conflict(row: dict[str, Any]) -> bool:
        if row.get("status") == "conflict":
            return True
        if row.get("agreement") == "conflict":
            return True
        if row.get("conflict_count"):
            return True
        if row.get("highest_severity") in {"error", "blocking"}:
            return True
        return False
