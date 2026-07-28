from __future__ import annotations

from collections import deque
from typing import Any

from services.tasks.models import AITask, TaskState, utc_now


class TaskManager:
    def __init__(self, backend_manager, history_limit: int = 100):
        self.backend_manager = backend_manager
        self._tasks: dict[str, AITask] = {}
        self._history = deque(maxlen=max(10, int(history_limit)))

    def execute_sync(
        self,
        task_type: str,
        payload: dict[str, Any],
        preferred_backend: str | None = None,
    ) -> AITask:
        task = AITask(
            task_type=task_type,
            payload=dict(payload),
            preferred_backend=preferred_backend,
        )
        self._tasks[task.id] = task
        task.state = TaskState.RUNNING
        task.started_at = utc_now()

        try:
            backend_id, result = self.backend_manager.execute(
                task.task_type,
                task.payload,
                preferred_backend=task.preferred_backend,
            )
            task.selected_backend = backend_id
            task.result = result
            task.state = TaskState.COMPLETED
        except Exception as exc:
            task.error = str(exc)
            task.state = TaskState.FAILED
        finally:
            task.finished_at = utc_now()
            self._history.appendleft(task.id)

        return task

    def get(self, task_id: str) -> dict[str, Any] | None:
        task = self._tasks.get(str(task_id))
        return task.as_dict() if task else None

    def status(self) -> dict[str, Any]:
        tasks = list(self._tasks.values())
        return {
            "total": len(tasks),
            "running": sum(
                task.state is TaskState.RUNNING for task in tasks
            ),
            "completed": sum(
                task.state is TaskState.COMPLETED for task in tasks
            ),
            "failed": sum(
                task.state is TaskState.FAILED for task in tasks
            ),
            "history": [
                self._tasks[task_id].as_dict()
                for task_id in list(self._history)[:10]
                if task_id in self._tasks
            ],
        }
