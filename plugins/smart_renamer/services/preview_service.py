from __future__ import annotations

from typing import Any

from mediahub_smart_renamer_runtime.services.rename_pipeline import RenamePipeline


class RenamePreviewService:
    def __init__(self, backend_registry, decision_hint_provider=None):
        self.pipeline = RenamePipeline(
            backend_registry,
            decision_hint_provider=decision_hint_provider,
        )

    def create_preview(
        self,
        *,
        items: list[dict[str, Any]],
        rules: list[dict[str, Any]],
        preferred_backend: str | None = None,
    ) -> dict[str, Any]:
        return self.pipeline.preview(
            items=items,
            rules=rules,
            preferred_backend=preferred_backend,
        )
