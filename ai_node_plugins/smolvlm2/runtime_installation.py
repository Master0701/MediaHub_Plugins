"""Safe installation planning for SmolVLM2.

This module intentionally separates planning from execution.
Creating a plan MUST NOT install or modify packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime_manifest import runtime_manifest
from runtime_provisioner import provision_plan
from runtime_status import runtime_status


class SmolVLM2InstallationError(RuntimeError):
    pass


def installation_plan(
    python_executable: str | Path,
    requested_backend: str = "auto",
) -> dict[str, Any]:

    python_path = Path(
        python_executable
    )

    if not python_path.is_file():
        raise SmolVLM2InstallationError(
            "Private Python wurde nicht gefunden: "
            + str(python_path)
        )

    before = runtime_status(
        python_path,
        requested_backend,
    )

    ready_before = bool(
        before.get(
            "ready",
            False,
        )
    )

    if ready_before:
        selected_backend = before.get(
            "selected_backend"
        )

        commands: list[list[str]] = []

    else:
        provision = provision_plan(
            python_path,
            requested_backend,
        )

        selected_backend = provision.get(
            "selected_backend"
        )

        commands = list(
            provision.get(
                "commands",
                [],
            )
        )

    return {
        "runtime": runtime_manifest(),
        "python": str(python_path),
        "requested_backend": requested_backend,
        "selected_backend": selected_backend,
        "ready_before": ready_before,
        "missing_modules_before": before.get(
            "missing_modules",
            [],
        ),
        "commands": commands,
        "requires_changes": not ready_before,
        "execute": False,
    }


def update_plan(
    python_executable: str | Path,
    requested_backend: str = "auto",
) -> dict[str, Any]:
    """Return an update plan without executing it."""

    plan = installation_plan(
        python_executable,
        requested_backend,
    )

    return {
        **plan,
        "operation": "update",
        "execute": False,
    }
