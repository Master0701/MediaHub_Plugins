"""Bridge to isolated SmolVLM2 runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class SmolVLM2RuntimeBridgeError(
    RuntimeError
):
    pass


def run_analysis(
    *,
    runtime_python: str | Path,
    runner_path: str | Path,
    job_type: str,
    input_path: str | Path,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:

    runtime_python = Path(
        runtime_python
    )

    runner_path = Path(
        runner_path
    )

    if not runtime_python.is_file():
        raise SmolVLM2RuntimeBridgeError(
            "Runtime-Python nicht gefunden: "
            f"{runtime_python}"
        )

    if not runner_path.is_file():
        raise SmolVLM2RuntimeBridgeError(
            "Runtime-Runner nicht gefunden: "
            f"{runner_path}"
        )

    request = {
        "job_type": str(job_type),
        "input_path": str(input_path),
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
    )

    stdout = (
        completed.stdout or ""
    ).strip()

    if not stdout:
        raise SmolVLM2RuntimeBridgeError(
            "SmolVLM2-Runtime lieferte "
            "keine JSON-Antwort. "
            f"stderr={completed.stderr!r}"
        )

    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SmolVLM2RuntimeBridgeError(
            "Ungueltige JSON-Antwort "
            "der SmolVLM2-Runtime."
        ) from exc

    if not response.get("ok"):
        error = dict(
            response.get("error")
            or {}
        )

        raise SmolVLM2RuntimeBridgeError(
            "SmolVLM2-Runtime-Fehler: "
            f"{error.get('type', 'Error')}: "
            f"{error.get('message', '')}"
        )

    if completed.returncode != 0:
        raise SmolVLM2RuntimeBridgeError(
            "SmolVLM2-Runtime endete mit "
            f"Code {completed.returncode}."
        )

    result = response.get("result")

    if not isinstance(result, dict):
        raise SmolVLM2RuntimeBridgeError(
            "SmolVLM2-Runtime lieferte "
            "kein Ergebnisobjekt."
        )

    return result
