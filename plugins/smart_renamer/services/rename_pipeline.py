from __future__ import annotations

from typing import Any

from mediahub_smart_renamer_runtime.services.conflict_service import ConflictService
from mediahub_smart_renamer_runtime.services.media_scanner import MediaScanner


class RenamePipeline:
    """Scanner → Backend → Konfliktmodell → PreviewModel."""

    def __init__(self, backend_registry, decision_hint_provider=None):
        self.backend_registry = backend_registry
        self.scanner = MediaScanner(
            decision_hint_provider=decision_hint_provider
        )
        self.conflicts = ConflictService()

    def preview(
        self,
        *,
        items: list[dict[str, Any]],
        rules: list[dict[str, Any]],
        preferred_backend: str | None = None,
    ) -> dict[str, Any]:
        media_items, skipped = self.scanner.scan(items)
        backend = self.backend_registry.select_backend(
            required_capabilities=["preview_changes"],
            preferred_backend=preferred_backend,
        )
        if backend is None:
            return {
                "status": "capability_unavailable",
                "backend_id": None,
                "changes": [],
                "preview_rows": [],
                "conflicts": [],
                "skipped": skipped,
                "automatic_execution": False,
                "requires_confirmation": True,
                "message": (
                    "Kein installiertes, aktiviertes und gesundes "
                    "Vorschau-Backend ist verfügbar."
                ),
            }

        backend_items = [
            {
                "path": str(item.path),
                "metadata": item.rule_metadata(),
                "media_model": item.to_dict(),
            }
            for item in media_items
        ]
        raw = backend.preview(backend_items, rules)
        rows, conflicts = self.conflicts.evaluate(
            list(raw.get("changes") or []),
            backend_id=backend.backend_id,
        )
        row_dicts = [row.to_dict() for row in rows]
        blocking = sum(1 for row in rows if row.blocked)
        warnings = sum(
            1
            for row in rows
            if row.highest_severity.value == "warning"
        )

        status = (
            "conflicts_found"
            if blocking
            else ("warnings_found" if warnings else "preview_ready")
        )
        return {
            **raw,
            "status": status,
            "selected_backend": backend.backend_id,
            "preview_rows": row_dicts,
            "conflicts": conflicts,
            "skipped": skipped,
            "media_items": [item.to_dict() for item in media_items],
            "automatic_install": True,
            "automatic_execution": False,
            "requires_confirmation": True,
            "summary": {
                **dict(raw.get("summary") or {}),
                "skipped_count": len(skipped),
                "blocking_count": blocking,
                "warning_row_count": warnings,
            },
        }
