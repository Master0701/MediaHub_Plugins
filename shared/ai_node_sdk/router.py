from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .availability import (
    PluginRuntimeStatus,
    check_availability,
)
from .execution import execute_task
from .loader import LoadedPlugin
from .task import TaskRequest, TaskResult


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    plugin_id: str
    plugin_name: str
    capability: str


def find_candidates(
    plugins: Iterable[LoadedPlugin],
    task_type: str,
    *,
    runtime_status: Mapping[str, PluginRuntimeStatus] | None = None,
    available_tools: Iterable[str] = (),
) -> tuple[RouteCandidate, ...]:
    capability = str(task_type).strip()
    status_map = runtime_status or {}

    candidates: list[RouteCandidate] = []

    for plugin in plugins:
        if not plugin.has_capability(capability):
            continue

        status = status_map.get(
            plugin.manifest.plugin_id,
            PluginRuntimeStatus(),
        )
        availability = check_availability(
            plugin,
            runtime=status,
            available_tools=available_tools,
        )
        if not availability.usable:
            continue

        candidates.append(
            RouteCandidate(
                plugin_id=plugin.manifest.plugin_id,
                plugin_name=plugin.manifest.name,
                capability=capability,
            )
        )

    return tuple(candidates)


def route_task(
    plugins: Iterable[LoadedPlugin],
    task: TaskRequest,
    *,
    runtime_status: Mapping[str, PluginRuntimeStatus] | None = None,
    available_tools: Iterable[str] = (),
) -> TaskResult:
    plugin_list = tuple(plugins)
    status_map = runtime_status or {}
    blocked_reasons: list[str] = []

    for plugin in plugin_list:
        if not plugin.has_capability(task.task_type):
            continue

        status = status_map.get(
            plugin.manifest.plugin_id,
            PluginRuntimeStatus(),
        )
        availability = check_availability(
            plugin,
            runtime=status,
            available_tools=available_tools,
        )

        if not availability.usable:
            detail = availability.reason
            if availability.missing_tools:
                detail += " Fehlend: " + ", ".join(
                    availability.missing_tools
                )
            blocked_reasons.append(
                f"{plugin.manifest.plugin_id}: {detail}"
            )
            continue

        return execute_task(plugin, task)

    if blocked_reasons:
        return TaskResult.failure(
            (
                f"Capability {task.task_type!r} ist vorhanden, "
                "aber aktuell kein passendes Plugin nutzbar. "
                + " | ".join(blocked_reasons)
            ),
            metadata={
                "request_id": task.request_id,
                "task_type": task.task_type,
            },
        )

    return TaskResult.failure(
        f"Keine installierte AI-Node-Erweiterung bietet "
        f"Capability {task.task_type!r}.",
        metadata={
            "request_id": task.request_id,
            "task_type": task.task_type,
        },
    )
