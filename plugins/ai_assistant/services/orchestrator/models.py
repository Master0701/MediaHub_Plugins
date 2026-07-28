from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class StepState(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class OrchestratorStep:
    id: str
    title: str
    task_type: str
    capability: str
    required_tools: list[str] = field(default_factory=list)
    state: StepState = StepState.PLANNED
    reason: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass(slots=True)
class OrchestratorPlan:
    request_type: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: uuid4().hex)
    execution_mode: str = "local_only"
    steps: list[OrchestratorStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_type": self.request_type,
            "execution_mode": self.execution_mode,
            "payload": dict(self.payload),
            "steps": [step.as_dict() for step in self.steps],
            "warnings": list(self.warnings),
        }
