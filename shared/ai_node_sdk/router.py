from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .availability import (
    PluginRuntimeStatus,
    check_availability,
)
from .execution import execute_task
from .loader import LoadedPlugin
from .selection import SelectionPolicy, rank_candidates
from .task import TaskRequest, TaskResult


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    plugin_id: str
    plugin_name: str
    capability: str
    priority: int = 0


def _usable_plugins(
    plugins: Iterable[LoadedPlugin],
    task_type: str,
    *,
    runtime_status: Mapping[str, PluginRuntimeStatus] | None,
    available_tools: Iterable[str],
    policy: SelectionPolicy | None,
) -> tuple[LoadedPlugin, ...]:
    capability = str(task_type).strip()
    status_map = runtime_status or {}
    usable: list[LoadedPlugin] = []

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
        if availability.usable:
            usable.append(plugin)

    return tuple(
        item.plugin
        for item in rank_candidates(usable, policy)
    )


def find_candidates(
    plugins: Iterable[LoadedPlugin],
    task_type: str,
    *,
    runtime_status: Mapping[str, PluginRuntimeStatus] | None = None,
    available_tools: Iterable[str] = (),
    policy: SelectionPolicy | None = None,
) -> tuple[RouteCandidate, ...]:
    active_policy = policy or SelectionPolicy()
    usable = _usable_plugins(
        plugins,
        task_type,
        runtime_status=runtime_status,
        available_tools=available_tools,
        policy=active_policy,
    )

    return tuple(
        RouteCandidate(
            plugin_id=plugin.manifest.plugin_id,
            plugin_name=plugin.manifest.name,
            capability=str(task_type).strip(),
            priority=active_policy.priority_for(
                plugin.manifest.plugin_id
            ),
        )
        for plugin in usable
    )


def route_task(
    plugins: Iterable[LoadedPlugin],
    task: TaskRequest,
    *,
    runtime_status: Mapping[str, PluginRuntimeStatus] | None = None,
    available_tools: Iterable[str] = (),
    policy: SelectionPolicy | None = None,
) -> TaskResult:
    plugin_list = tuple(plugins)
    status_map = runtime_status or {}
    active_policy = policy or SelectionPolicy()

    blocked_reasons: list[str] = []
    capability_plugins: list[LoadedPlugin] = []

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

        capability_plugins.append(plugin)

    ranked = rank_candidates(
        capability_plugins,
        active_policy,
    )

    execution_errors: list[str] = []

    for index, candidate in enumerate(ranked):
        result = execute_task(candidate.plugin, task)

        if result.ok:
            metadata = dict(result.metadata)
            metadata.update(
                {
                    "selected_plugin_id":
                        candidate.plugin.manifest.plugin_id,
                    "selection_priority": candidate.priority,
                    "fallback_index": index,
                }
            )
            return TaskResult(
                ok=True,
                data=dict(result.data),
                error=result.error,
                backend=result.backend,
                metadata=metadata,
            )

        execution_errors.append(
            f"{candidate.plugin.manifest.plugin_id}: "
            f"{result.error or 'Ausführung fehlgeschlagen.'}"
        )

        if not active_policy.allow_fallback:
            break

    if execution_errors:
        return TaskResult.failure(
            (
                f"Capability {task.task_type!r} konnte von keinem "
                "ausgewählten Plugin erfolgreich ausgeführt werden. "
                + " | ".join(execution_errors)
            ),
            metadata={
                "request_id": task.request_id,
                "task_type": task.task_type,
                "attempt_count": len(execution_errors),
            },
        )

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
