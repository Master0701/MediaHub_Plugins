from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HealthProvider(Protocol):
    """Minimaler Laufzeitvertrag für AI-Node-Plugins."""

    def health(self) -> dict[str, Any]:
        ...


@runtime_checkable
class TaskExecutor(Protocol):
    """Optionaler einheitlicher Auftragseinstieg für neue Plugins."""

    def execute(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ...


def supports_health(plugin: object) -> bool:
    return isinstance(plugin, HealthProvider)


def supports_task_executor(plugin: object) -> bool:
    return isinstance(plugin, TaskExecutor)
