from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TaskRequest:
    task_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    backend: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        data: dict[str, Any] | None = None,
        *,
        backend: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "TaskResult":
        return cls(
            ok=True,
            data=dict(data or {}),
            backend=backend,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failure(
        cls,
        error: str,
        *,
        backend: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "TaskResult":
        return cls(
            ok=False,
            error=str(error),
            backend=backend,
            metadata=dict(metadata or {}),
        )
