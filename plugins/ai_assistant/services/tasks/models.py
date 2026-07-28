from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class AITask:
    task_type: str
    payload: dict[str, Any]
    preferred_backend: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    state: TaskState = TaskState.PENDING
    selected_backend: str | None = None
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data
