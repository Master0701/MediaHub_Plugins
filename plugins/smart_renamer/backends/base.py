from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RenamerBackend(ABC):
    backend_id = "unknown"
    display_name = "Unknown backend"
    platform_names: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def probe(self) -> dict[str, Any]:
        """Return actual availability and health information."""

    @abstractmethod
    def preview(
        self,
        items: list[dict[str, Any]],
        rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a non-destructive rename preview."""

    def execute(self, *args, **kwargs):
        raise RuntimeError(
            f"Backend {self.backend_id!r} does not allow execution yet."
        )
