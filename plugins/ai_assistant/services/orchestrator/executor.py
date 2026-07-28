from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from services.orchestrator.models import OrchestratorPlan, StepState


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class LocalOrchestratorExecutor:
    EXECUTABLE_TASKS = {"media.analyze"}

    def __init__(self, task_manager):
        self.task_manager = task_manager

    def execute(self, plan: OrchestratorPlan) -> dict[str, Any]:
        started_at = utc_now()
        executed = 0
        failed = 0

        for step in plan.steps:
            if step.state is StepState.BLOCKED:
                continue
            if step.task_type not in self.EXECUTABLE_TASKS:
                step.state = StepState.SKIPPED
                step.reason = (
                    "Der Schritt ist geplant, aber in v1.2.0 noch nicht ausführbar."
                )
                continue

            step.state = StepState.RUNNING
            task = self.task_manager.execute_sync(
                step.task_type,
                plan.payload,
                preferred_backend="local",
            )
            if task.error:
                step.state = StepState.FAILED
                step.error = task.error
                failed += 1
                continue

            step.state = StepState.COMPLETED
            step.result = dict(task.result or {})
            executed += 1

        primary_result: dict[str, Any] = {}
        for step in plan.steps:
            if step.task_type == "media.analyze" and step.state is StepState.COMPLETED:
                primary_result = dict(step.result or {})
                break

        return {
            "result": primary_result,
            "orchestration": {
                "plan": plan.as_dict(),
                "execution_mode": "local_only",
                "started_at": started_at,
                "finished_at": utc_now(),
                "executed_steps": executed,
                "failed_steps": failed,
                "blocked_steps": sum(step.state is StepState.BLOCKED for step in plan.steps),
                "skipped_steps": sum(step.state is StepState.SKIPPED for step in plan.steps),
            },
        }
