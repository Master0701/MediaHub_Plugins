from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .loader import LoadedPlugin
from .task import TaskRequest, TaskResult


@dataclass(frozen=True, slots=True)
class ExecutionDecision:
    accepted: bool
    capability: str
    reason: str = ""


# Dies ist KEINE zweite Capability-Liste.
# Es beschreibt nur den standardisierten Methodennamen für bekannte
# Capability-Verträge. Ob ein Plugin eine Capability besitzt, kommt
# weiterhin ausschließlich aus dessen plugin.json.
CAPABILITY_METHOD_ALIASES: dict[str, str] = {
    "health_check": "health",
    "test_provider": "test",
}


def check_capability(
    plugin: LoadedPlugin,
    task: TaskRequest,
) -> ExecutionDecision:
    capability = task.task_type.strip()

    if not capability:
        return ExecutionDecision(
            accepted=False,
            capability="",
            reason="task_type ist leer.",
        )

    if not plugin.has_capability(capability):
        return ExecutionDecision(
            accepted=False,
            capability=capability,
            reason=(
                f"Plugin {plugin.manifest.plugin_id} meldet "
                f"Capability {capability!r} nicht."
            ),
        )

    return ExecutionDecision(
        accepted=True,
        capability=capability,
    )


def _result_from_plugin(
    plugin: LoadedPlugin,
    task: TaskRequest,
    result: Any,
) -> TaskResult:
    metadata = {
        "request_id": task.request_id,
        "task_type": task.task_type,
    }

    if isinstance(result, TaskResult):
        return result

    if isinstance(result, dict):
        ok = bool(result.get("ok", True))
        if ok:
            return TaskResult.success(
                result,
                backend=plugin.manifest.plugin_id,
                metadata=metadata,
            )
        return TaskResult.failure(
            str(result.get("error") or "Plugin meldet Fehler."),
            backend=plugin.manifest.plugin_id,
            metadata=metadata,
        )

    return TaskResult.success(
        {"result": result},
        backend=plugin.manifest.plugin_id,
        metadata=metadata,
    )


def _call_method(
    method: Any,
    payload: dict[str, Any],
) -> Any:
    try:
        return method(**payload)
    except TypeError:
        # Rückwärtskompatibilität für einfache bestehende Methoden,
        # die genau einen Positionswert erwarten.
        if len(payload) == 1:
            return method(next(iter(payload.values())))
        raise


def execute_task(
    plugin: LoadedPlugin,
    task: TaskRequest,
) -> TaskResult:
    decision = check_capability(plugin, task)

    if not decision.accepted:
        return TaskResult.failure(
            decision.reason,
            backend=plugin.manifest.plugin_id,
            metadata={
                "request_id": task.request_id,
                "task_type": task.task_type,
            },
        )

    instance = plugin.instance

    # Neue Plugins dürfen einen einheitlichen execute()-Einstieg anbieten.
    execute = getattr(instance, "execute", None)
    if callable(execute):
        try:
            result = execute(
                task.task_type,
                dict(task.payload),
            )
        except Exception as exc:
            return TaskResult.failure(
                str(exc),
                backend=plugin.manifest.plugin_id,
                metadata={
                    "request_id": task.request_id,
                    "task_type": task.task_type,
                },
            )

        return _result_from_plugin(plugin, task, result)

    # Bestehende Plugins bleiben kompatibel:
    # 1. gleichnamige Methode,
    # 2. standardisierter Capability->Methoden-Vertrag.
    method_name = task.task_type
    method = getattr(instance, method_name, None)

    if not callable(method):
        method_name = CAPABILITY_METHOD_ALIASES.get(
            task.task_type,
            task.task_type,
        )
        method = getattr(instance, method_name, None)

    if not callable(method):
        return TaskResult.failure(
            (
                f"Capability {task.task_type!r} ist im Manifest vorhanden, "
                f"aber keine ausführbare Methode wurde gefunden."
            ),
            backend=plugin.manifest.plugin_id,
            metadata={
                "request_id": task.request_id,
                "task_type": task.task_type,
            },
        )

    try:
        result = _call_method(
            method,
            dict(task.payload),
        )
    except Exception as exc:
        return TaskResult.failure(
            str(exc),
            backend=plugin.manifest.plugin_id,
            metadata={
                "request_id": task.request_id,
                "task_type": task.task_type,
                "method": method_name,
            },
        )

    return _result_from_plugin(plugin, task, result)
