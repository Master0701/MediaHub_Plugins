"""Python runtime selection for SmolVLM2."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

SUPPORTED_MAJOR = 3
SUPPORTED_MINORS = (13, 12, 11, 10, 9)
PREFERRED_MINOR = 12


class RuntimePythonError(RuntimeError):
    pass


def inspect_python(
    executable: str | Path,
) -> dict[str, Any]:
    executable = Path(executable)

    if not executable.is_file():
        return {
            "executable": str(executable),
            "available": False,
            "supported": False,
        }

    code = (
        "import json,platform,sys;"
        "print(json.dumps({"
        "'major':sys.version_info.major,"
        "'minor':sys.version_info.minor,"
        "'micro':sys.version_info.micro,"
        "'bits':platform.architecture()[0],"
        "'executable':sys.executable"
        "}))"
    )

    completed = subprocess.run(
        [
            str(executable),
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if completed.returncode != 0:
        return {
            "executable": str(executable),
            "available": True,
            "supported": False,
            "error": (
                completed.stderr or ""
            ).strip(),
        }

    try:
        data = json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "executable": str(executable),
            "available": True,
            "supported": False,
            "error": str(exc),
        }

    supported = (
        data.get("major")
        == SUPPORTED_MAJOR
        and data.get("minor")
        in SUPPORTED_MINORS
        and data.get("bits")
        == "64bit"
    )

    return {
        **data,
        "available": True,
        "supported": supported,
    }


def configured_python() -> Path | None:
    value = os.environ.get(
        "MEDIAHUB_SMOLVLM2_PYTHON"
    )

    if not value:
        return None

    return Path(value)


def mediahub_data_root() -> Path:
    """Persistent user data, independent of the Compute Node executable runtime."""
    override = os.environ.get("MEDIAHUB_COMPUTE_RUNTIME") or os.environ.get("MEDIAHUB_COMPUTE_DATA_ROOT")
    return Path(override).expanduser() if override else Path.home() / ".mediahub" / "compute_node"


def managed_python_candidates() -> list[Path]:
    """Prefer a verified portable Astral runtime; retain legacy candidate."""
    parent = mediahub_data_root() / "private_python"
    return [
        parent / "cpython-3.12.10-x64-astral-20250409" / "python.exe",
        parent / "cpython-3.12.10-x64" / "python.exe",
    ]

def private_python() -> Path | None:
    """Return the managed private SmolVLM2 Python."""

    for executable in managed_python_candidates():
        if executable.is_file():
            return executable
    return None


def launcher_candidates() -> list[Path]:
    """Return compatible Python candidates provided by the host."""

    candidates: list[Path] = []

    if os.name == "nt":
        launcher = shutil.which("py")

        if not launcher:
            return candidates

        for minor in SUPPORTED_MINORS:
            completed = subprocess.run(
                [
                    launcher,
                    f"-3.{minor}",
                    "-c",
                    (
                        "import sys;"
                        "print(sys.executable)"
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                check=False,
            )

            if completed.returncode != 0:
                continue

            value = (
                completed.stdout
                or ""
            ).strip()

            if value:
                path = Path(value)

                if path not in candidates:
                    candidates.append(path)

        return candidates

    for name in ("python3", "python"):
        value = shutil.which(name)

        if not value:
            continue

        path = Path(value)

        if path not in candidates:
            candidates.append(path)

    return candidates


def discover_python() -> dict[str, Any]:
    if os.name == "nt":
        checked = []
        for private in managed_python_candidates():
            if not private.is_file():
                continue
            status = inspect_python(private)
            status["managed"] = True
            version_ok = (
                status.get("major") == 3
                and status.get("minor") == 12
                and status.get("micro") == 10
                and status.get("bits") == "64bit"
            )
            modules_ok = False
            if version_ok:
                try:
                    check = subprocess.run(
                        [str(private), "-I", "-c", "import venv, ensurepip"],
                        capture_output=True, text=True, timeout=15, check=False,
                    )
                    modules_ok = check.returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    pass
            status["supported"] = version_ok and modules_ok
            checked.append(status)
            if status["supported"]:
                return {
                    "found": True,
                    "source": "mediahub_astral" if "-astral-" in str(private) else "mediahub_private",
                    "python": status,
                    "checked": checked,
                }

        return {
            "found": False,
            "source": None,
            "python": None,
            "checked": checked,
            "required": {
                "major": 3,
                "preferred_minor": 12,
                "architecture": "64bit",
                "managed": True,
            },
        }

    configured = configured_python()

    checked = []

    if configured is not None:
        status = inspect_python(
            configured
        )

        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "configured",
                "python": status,
                "checked": checked,
            }

    private = private_python()

    if private is not None:
        status = inspect_python(
            private
        )

        status["managed"] = True

        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "mediahub_private",
                "python": status,
                "checked": checked,
            }

    for candidate in launcher_candidates():
        status = inspect_python(
            candidate
        )

        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "launcher",
                "python": status,
                "checked": checked,
            }

    return {
        "found": False,
        "source": None,
        "python": None,
        "checked": checked,
        "required": {
            "major": SUPPORTED_MAJOR,
            "preferred_minor": (
                PREFERRED_MINOR
            ),
            "supported_minors": list(
                SUPPORTED_MINORS
            ),
            "architecture": "64bit",
        },
    }


def require_python() -> Path:
    result = discover_python()

    if not result["found"]:
        raise RuntimePythonError(
            "Keine kompatible isolierte "
            "SmolVLM2-Python-Runtime gefunden. "
            "Bevorzugt wird Python 3.12 x64 unter Windows "
            "bzw. ein kompatibles Python 3 unter Linux."
        )

    return Path(
        result["python"]["executable"]
    )
