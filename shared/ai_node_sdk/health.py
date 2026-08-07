from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_HEALTH_STATES = frozenset(
    {"online", "degraded", "offline"}
)


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    plugin_id: str
    plugin: str
    version: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_HEALTH_STATES:
            raise ValueError(
                f"Ungültiger Health-Status: {self.status}"
            )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "plugin_id": self.plugin_id,
            "plugin": self.plugin,
            "version": self.version,
        }
        if self.message:
            payload["message"] = self.message
        if self.details:
            payload["details"] = dict(self.details)
        return payload
