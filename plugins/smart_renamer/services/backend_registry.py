from __future__ import annotations

from pathlib import Path
from typing import Any

from mediahub_smart_renamer_runtime.backends.external import ReNamerWindowsBackend
from mediahub_smart_renamer_runtime.backends.native import NativeRenamerBackend


class RenamerBackendRegistry:
    REQUIRED_HEALTH_FIELDS = (
        "installed",
        "enabled",
        "reachable",
        "healthy",
        "platform_compatible",
    )

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.backends = [
            NativeRenamerBackend(),
            ReNamerWindowsBackend(base_dir=self.base_dir),
        ]
        self.preferred_backend_id = "renamer_windows"
        self.fallback_backend_id = "mediahub_native"
        self.status_by_id: dict[str, dict[str, Any]] = {}
        self.refresh()

    def refresh(self) -> dict[str, dict[str, Any]]:
        statuses: dict[str, dict[str, Any]] = {}
        for backend in self.backends:
            status = dict(backend.probe() or {})
            status.setdefault("backend_id", backend.backend_id)
            status.setdefault("display_name", backend.display_name)
            status.setdefault("capabilities", list(backend.capabilities))
            status.setdefault(
                "priority",
                int(getattr(backend, "priority", 1000)),
            )
            status.setdefault("tool_id", getattr(backend, "tool_id", None))
            status.setdefault("homepage", getattr(backend, "homepage", ""))
            status.setdefault(
                "license",
                getattr(backend, "license_name", ""),
            )
            status.setdefault(
                "preview_bridge_ready",
                bool(getattr(backend, "preview_bridge_ready", False)),
            )
            status.setdefault(
                "execution_bridge_ready",
                bool(getattr(backend, "execution_bridge_ready", False)),
            )
            status.setdefault(
                "configuration_ready",
                backend.backend_id == "mediahub_native",
            )
            statuses[backend.backend_id] = status

        self.status_by_id = statuses
        return dict(self.status_by_id)

    @classmethod
    def _usable(cls, status: dict[str, Any]) -> bool:
        return all(
            bool(status.get(field))
            for field in cls.REQUIRED_HEALTH_FIELDS
        )

    def describe_backends(self) -> list[dict[str, Any]]:
        return [
            dict(
                self.status_by_id.get(backend.backend_id)
                or backend.probe()
            )
            for backend in self.backends
        ]

    def get_capability_status(self) -> dict[str, Any]:
        usable = [
            status
            for status in self.status_by_id.values()
            if self._usable(status)
        ]
        capabilities = sorted({
            capability
            for status in usable
            for capability in status.get("capabilities") or []
        })
        preferred = self.status_by_id.get(self.preferred_backend_id) or {}
        fallback = self.status_by_id.get(self.fallback_backend_id) or {}
        active_preview = next(
            (
                status.get("backend_id")
                for status in sorted(
                    usable,
                    key=lambda item: int(item.get("priority", 1000)),
                )
                if bool(status.get("preview_bridge_ready"))
                and "preview_changes" in set(status.get("capabilities") or [])
            ),
            None,
        )
        return {
            "usable_backend_count": len(usable),
            "usable_backend_ids": [
                item["backend_id"] for item in usable
            ],
            "available_capabilities": capabilities,
            "automatic_install": True,
            "discovery_checked": True,
            "node_type": "mediahub_windows",
            "preferred_backend_id": (
                self.preferred_backend_id
                if self._usable(preferred)
                else None
            ),
            "preferred_backend_ready": self._usable(preferred),
            "active_preview_backend_id": active_preview,
            "fallback_backend_id": (
                self.fallback_backend_id
                if self._usable(fallback)
                else None
            ),
        }

    def select_backend(
        self,
        required_capabilities: list[str],
        preferred_backend: str | None = None,
    ):
        required = set(required_capabilities)
        candidates = []

        for backend in self.backends:
            status = self.status_by_id.get(backend.backend_id) or {}
            if not self._usable(status):
                continue
            if not required.issubset(
                set(status.get("capabilities") or [])
            ):
                continue
            candidates.append(backend)

        candidates.sort(
            key=lambda backend: int(
                (self.status_by_id.get(backend.backend_id) or {}).get(
                    "priority",
                    1000,
                )
            )
        )

        if preferred_backend:
            for backend in candidates:
                status = self.status_by_id.get(backend.backend_id) or {}
                if (
                    backend.backend_id == preferred_backend
                    and bool(status.get("preview_bridge_ready"))
                ):
                    return backend

        for backend in candidates:
            status = self.status_by_id.get(backend.backend_id) or {}
            if bool(status.get("preview_bridge_ready")):
                return backend

        return None
