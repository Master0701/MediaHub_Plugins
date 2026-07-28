from __future__ import annotations

from typing import Any

from services.backends.base import (
    AIBackend,
    BackendCapability,
    BackendStatus,
)


class LocalBackend(AIBackend):
    id = "local"
    name = "Interne MediaHub-KI"
    backend_type = "local"

    def __init__(self, media_analyzer):
        self.media_analyzer = media_analyzer

    def status(self) -> BackendStatus:
        return BackendStatus(
            id=self.id,
            name=self.name,
            available=True,
            backend_type=self.backend_type,
            message="Lokales Backend ist verfügbar.",
            capabilities=(
                BackendCapability(
                    id="media.analyze",
                    tools=("ffprobe", "mediainfo"),
                ),
                BackendCapability(id="knowledge.search"),
                BackendCapability(id="quality.evaluate"),
                BackendCapability(id="fingerprint.register"),
            ),
            metadata={
                "requires_network": False,
                "controls_mediahub": True,
            },
        )

    def supports(self, task_type: str, payload: dict[str, Any]) -> bool:
        return task_type == "media.analyze"

    def execute(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if task_type != "media.analyze":
            raise ValueError(
                f"Aufgabentyp wird lokal noch nicht unterstützt: {task_type}"
            )

        file_path = payload.get("file_path")
        if not file_path:
            raise ValueError("Für media.analyze fehlt file_path.")

        return self.media_analyzer.analyze(
            file_path,
            force=bool(payload.get("force", False)),
        )
