from __future__ import annotations

from typing import Any

from services.backends.ai_node_backend import AINodeBackend
from services.backends.local_backend import LocalBackend


class BackendManager:
    def __init__(
        self,
        media_analyzer,
        ai_node_config: dict[str, Any] | None = None,
    ):
        config = ai_node_config or {}
        self.local = LocalBackend(media_analyzer)
        self.ai_node = AINodeBackend(
            host=str(config.get("host") or ""),
            port=int(config.get("port") or 8765),
            api_token=str(config.get("api_token") or ""),
            timeout=float(config.get("timeout") or 4.0),
        )
        self._backends = (self.local, self.ai_node)

    def update_ai_node_config(
        self,
        config: dict[str, Any] | None,
    ) -> None:
        """Übernimmt geänderte MediaHub-AI-Node-Einstellungen."""

        values = dict(config or {})
        self.ai_node = AINodeBackend(
            host=str(values.get("host") or ""),
            port=int(values.get("port") or 8765),
            api_token=str(values.get("api_token") or ""),
            timeout=float(values.get("timeout") or 4.0),
        )
        self._backends = (self.local, self.ai_node)

    def status(self) -> dict[str, Any]:
        statuses = [
            backend.status().as_dict()
            for backend in self._backends
        ]
        return {
            "default_backend": self.local.id,
            "fallback_backend": self.local.id,
            "backends": statuses,
            "available": [
                item["id"]
                for item in statuses
                if item["available"]
            ],
        }

    def select(
        self,
        task_type: str,
        payload: dict[str, Any],
        preferred_backend: str | None = None,
    ):
        candidates = list(self._backends)

        if preferred_backend:
            candidates.sort(
                key=lambda backend: backend.id != preferred_backend
            )
        elif payload.get("prefer_ai_node"):
            candidates.sort(
                key=lambda backend: backend.id != "ai_node"
            )

        for backend in candidates:
            status = backend.status()
            if status.available and backend.supports(task_type, payload):
                return backend

        if self.local.supports(task_type, payload):
            return self.local

        raise RuntimeError(
            f"Kein Backend unterstützt die Aufgabe {task_type}."
        )

    def execute(
        self,
        task_type: str,
        payload: dict[str, Any],
        preferred_backend: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        backend = self.select(
            task_type,
            payload,
            preferred_backend=preferred_backend,
        )
        try:
            return backend.id, backend.execute(task_type, payload)
        except Exception:
            if (
                backend.id != self.local.id
                and self.local.supports(task_type, payload)
            ):
                return self.local.id, self.local.execute(
                    task_type,
                    payload,
                )
            raise
