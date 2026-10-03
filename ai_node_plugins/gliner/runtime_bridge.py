"""Bridge to the isolated GLiNER runtime."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class GLiNERRuntimeBridgeError(RuntimeError):
    pass


def _subprocess_environment(
    *,
    packages_path: Path,
    execution: dict[str, Any],
) -> dict[str, str]:
    """Build environment for the isolated GLiNER process."""

    environment = os.environ.copy()

    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    environment["MEDIAHUB_GLINER_PACKAGES"] = str(
        packages_path
    )

    old_pythonpath = environment.get(
        "PYTHONPATH",
        "",
    )

    environment["PYTHONPATH"] = (
        str(packages_path)
        if not old_pythonpath
        else str(packages_path)
        + os.pathsep
        + old_pythonpath
    )

    backend = str(
        execution.get(
            "backend",
            "cpu",
        )
    ).strip().lower()

    environment["MEDIAHUB_GLINER_BACKEND"] = backend

    return environment


def run_analysis(
    *,
    runtime_python: str | Path,
    packages_path: str | Path,
    runner_path: str | Path,
    text: str,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:

    runtime_python = Path(runtime_python)
    packages_path = Path(packages_path)
    runner_path = Path(runner_path)

    if not runtime_python.is_file():
        raise GLiNERRuntimeBridgeError(
            "Runtime-Python nicht gefunden: "
            f"{runtime_python}"
        )

    if not packages_path.is_dir():
        raise GLiNERRuntimeBridgeError(
            "GLiNER-Paketverzeichnis nicht gefunden: "
            f"{packages_path}"
        )

    if not runner_path.is_file():
        raise GLiNERRuntimeBridgeError(
            "Runtime-Runner nicht gefunden: "
            f"{runner_path}"
        )

    request = {
        "packages_path": str(
            packages_path.resolve()
        ),
        "text": str(text),
        "execution": dict(execution),
        "options": dict(options or {}),
    }

    completed = subprocess.run(
        [
            str(runtime_python),
            str(runner_path),
        ],
        input=json.dumps(
            request,
            ensure_ascii=False,
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        check=False,
        env=_subprocess_environment(
            packages_path=packages_path,
            execution=execution,
        ),
    )

    stdout = (
        completed.stdout or ""
    ).strip()

    if not stdout:
        raise GLiNERRuntimeBridgeError(
            "GLiNER-Runtime lieferte "
            "keine JSON-Antwort. "
            f"stderr={completed.stderr!r}"
        )

    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise GLiNERRuntimeBridgeError(
            "Ungueltige JSON-Antwort "
            "der GLiNER-Runtime. "
            f"stdout={stdout!r} "
            f"stderr={completed.stderr!r}"
        ) from exc

    if not response.get("ok"):
        error = dict(
            response.get("error")
            or {}
        )

        raise GLiNERRuntimeBridgeError(
            "GLiNER-Runtime-Fehler: "
            f"{error.get('type', 'Error')}: "
            f"{error.get('message', '')}"
        )

    if completed.returncode != 0:
        raise GLiNERRuntimeBridgeError(
            "GLiNER-Runtime endete mit "
            f"Code {completed.returncode}."
        )

    result = response.get("result")

    if not isinstance(result, dict):
        raise GLiNERRuntimeBridgeError(
            "GLiNER-Runtime lieferte "
            "kein Ergebnisobjekt."
        )

    return result
