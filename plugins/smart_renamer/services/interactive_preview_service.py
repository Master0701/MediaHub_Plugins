from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from services.relation_preview_service import RelationPreviewService
from services.review_service import ReviewService

class InteractivePreviewService:
    def __init__(self, relation_preview_service: RelationPreviewService):
        self.relation_preview_service = relation_preview_service
        self.review_service = ReviewService()

    @staticmethod
    def item_id(path: str | Path) -> str:
        return hashlib.sha1(str(Path(path)).encode("utf-8")).hexdigest()[:16]

    def build(self, items, *, profile_id: str = "plex") -> dict[str, Any]:
        rows = []
        groups: dict[str, dict[str, Any]] = {}

        for item in items:
            preview = self.relation_preview_service.build_preview(item, profile_id=profile_id)
            relation = dict((item.detection_data or {}).get("media_relation") or {})
            decision = dict((item.detection_data or {}).get("decision") or {})
            confidence = float(
                relation.get("confidence")
                or decision.get("confidence")
                or (item.detection_data or {}).get("confidence")
                or 0
            )
            status = "review" if preview.review_required else "safe"
            if relation.get("relation_type") == "unknown_relation":
                status = "conflict"

            row = {
                "id": self.item_id(item.path),
                "path": str(item.path),
                "current_name": Path(item.path).name,
                "suggested_name": preview.suggested_name,
                "media_type": item.media_type,
                "title": item.title,
                "season": item.season,
                "episode": item.episode,
                "relation_type": preview.relation_type,
                "profile_id": preview.profile_id,
                "profile_name": preview.profile_name,
                "recommended_action": preview.recommended_action,
                "confidence": confidence,
                "review_required": preview.review_required,
                "status": status,
                "warnings": preview.warnings,
                "options": preview.options,
                "companion_count": len(getattr(item, "companion_files", []) or []),
            }
            row["review_reasons"] = self.review_service.classify(row)
            row["human_review_required"] = self.review_service.needs_human_review(row)
            rows.append(row)

            key = (
                f"series:season:{str(item.season or '00').zfill(2)}"
                if item.media_type == "series"
                else (item.media_type or "unknown")
            )
            label = (
                f"Staffel {str(item.season or '00').zfill(2)}"
                if item.media_type == "series"
                else ("Filme" if item.media_type == "movie" else "Sonstige")
            )
            group = groups.setdefault(key, {
                "key": key,
                "label": label,
                "media_type": item.media_type,
                "count": 0,
                "review_count": 0,
                "conflict_count": 0,
            })
            group["count"] += 1
            group["review_count"] += int(status == "review")
            group["conflict_count"] += int(status == "conflict")

        return {
            "summary": {
                "total": len(rows),
                "safe": sum(r["status"] == "safe" for r in rows),
                "review": sum(r["status"] == "review" for r in rows),
                "conflict": sum(r["status"] == "conflict" for r in rows),
                "profile_id": profile_id,
            },
            "groups": list(groups.values()),
            "rows": rows,
            "execution_locked": True,
        }
