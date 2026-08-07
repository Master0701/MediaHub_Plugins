from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .task import TaskRequest, TaskResult


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_JOB_STATUSES = frozenset(
    {
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class Job:
    request: TaskRequest
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: str = ""
    node_id: str = ""
    worker_id: str = ""
    result: TaskResult | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_JOB_STATUSES

    def with_update(self, **changes: Any) -> "Job":
        changes.setdefault("updated_at", utc_now_iso())
        return replace(self, **changes)
