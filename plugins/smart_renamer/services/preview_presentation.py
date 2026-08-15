from __future__ import annotations

import os
from typing import Any


class PreviewPresentationService:
    @staticmethod
    def _key(value: str) -> str:
        return os.path.normcase(os.path.abspath(str(value or "")))

    def enrich(self, result: dict[str, Any]) -> dict[str, Any]:
        payload = dict(result or {})
        media_items = list(payload.get("media_items") or [])
        rows = [dict(row) for row in (payload.get("preview_rows") or payload.get("changes") or [])]
        by_path = {
            self._key(item.get("path")): item
            for item in media_items
            if item.get("path")
        }
        relation_counts: dict[str, int] = {}
        review_count = 0

        for row in rows:
            media = by_path.get(self._key(row.get("source_path"))) or {}
            detection = dict(media.get("detection_data") or {})
            relation = dict(detection.get("media_relation") or {})
            decision = dict(detection.get("decision") or {})

            relation_type = str(relation.get("relation_type") or "single")
            confidence = float(
                relation.get("confidence")
                or decision.get("confidence")
                or detection.get("decision_confidence")
                or detection.get("confidence")
                or media.get("detection_confidence")
                or 0
            )
            review_required = bool(
                relation.get("review_required")
                or decision.get("review_required")
                or detection.get("review_required")
            )

            row["relation_type"] = relation_type
            row["confidence"] = confidence
            row["review_required"] = review_required
            row["media_type"] = str(media.get("media_type") or "unknown")
            row["season"] = str(media.get("season") or "")
            row["episode"] = str(media.get("episode") or "")
            row["episode_end"] = str(media.get("episode_end") or "")
            row["selected_candidate_id"] = str(
                detection.get("selected_candidate_id") or ""
            )
            row["detection_candidates"] = [
                dict(item or {})
                for item in (detection.get("candidates") or [])
            ]
            row["candidate_count"] = len(row["detection_candidates"])
            row["decision_state"] = str(
                decision.get("state")
                or detection.get("decision_state")
                or ""
            )
            row["decision_reason"] = str(decision.get("reason") or "")
            row["decision_confidence"] = float(
                decision.get("confidence")
                or detection.get("decision_confidence")
                or 0
            )

            relation_counts[relation_type] = relation_counts.get(relation_type, 0) + 1
            review_count += int(review_required)

        payload["preview_rows"] = rows
        payload["presentation_summary"] = {
            "relations": relation_counts,
            "review_required": review_count,
            "rows": len(rows),
        }
        return payload
