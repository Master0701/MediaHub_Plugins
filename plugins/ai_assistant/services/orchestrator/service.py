from __future__ import annotations

from typing import Any

from services.orchestrator.executor import LocalOrchestratorExecutor
from services.orchestrator.planner import LocalOrchestratorPlanner


class LocalAIOrchestrator:
    def __init__(self, capability_manager, task_manager):
        self.planner = LocalOrchestratorPlanner(capability_manager)
        self.executor = LocalOrchestratorExecutor(task_manager)
        self._last_run: dict[str, Any] | None = None

    def run(self, request_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        plan = self.planner.create_plan(request_type, payload)
        self._last_run = self.executor.execute(plan)
        return dict(self._last_run)

    def preview(self, request_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.planner.create_plan(request_type, payload).as_dict()

    def status(self) -> dict[str, Any]:
        return {
            "mode": "local_only",
            "remote_execution": False,
            "cloud_execution": False,
            "last_run": self._last_run,
            "supported_requests": ["media.analyze", "media.identify"],
        }
