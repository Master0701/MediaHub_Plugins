from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BackendCapability:
    id: str
    available: bool = True
    reason: str = ""
    tools: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tools"] = list(self.tools)
        return data


@dataclass(frozen=True, slots=True)
class BackendStatus:
    id: str
    name: str
    available: bool
    backend_type: str
    message: str = ""
    capabilities: tuple[BackendCapability, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "available": self.available,
            "backend_type": self.backend_type,
            "message": self.message,
            "capabilities": [
                capability.as_dict()
                for capability in self.capabilities
            ],
            "metadata": dict(self.metadata),
        }


class AIBackend(ABC):
    id = "unknown"
    name = "Unbekanntes Backend"
    backend_type = "unknown"

    @abstractmethod
    def status(self) -> BackendStatus:
        raise NotImplementedError

    @abstractmethod
    def supports(self, task_type: str, payload: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
