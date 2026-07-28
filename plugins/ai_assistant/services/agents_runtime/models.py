from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    id: str
    name: str
    capability: str
    task_type: str
    required_tools: tuple[str, ...] = ()
    implemented: bool = False
    category: str = "analysis"
    can_run_parallel: bool = False
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_tools"] = list(self.required_tools)
        return data


@dataclass(slots=True)
class AgentStatus:
    definition: AgentDefinition
    available: bool
    missing_tools: list[str] = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.definition.id,
            "name": self.definition.name,
            "capability": self.definition.capability,
            "task_type": self.definition.task_type,
            "required_tools": list(self.definition.required_tools),
            "implemented": self.definition.implemented,
            "category": self.definition.category,
            "can_run_parallel": self.definition.can_run_parallel,
            "description": self.definition.description,
            "available": self.available,
            "missing_tools": list(self.missing_tools),
            "reason": self.reason,
        }
