"""Gemeinsame portable Python-Runtime fuer Windows Compute Nodes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


PYTHON_VERSION = "3.12.10"


def runtime_root() -> Path:
    base = os.environ.get("MEDIAHUB_COMPUTE_RUNTIME")

    if base:
        root = Path(base)
    else:
        root = Path.home() / ".mediahub" / "compute_node"

    return root / "private_python" / f"cpython-{PYTHON_VERSION}-x64-astral-20250409"


def runtime_candidates() -> list[Path]:
    """Known managed locations, keeping the configured location first."""
    configured = runtime_root()
    home = Path.home() / ".mediahub" / "compute_node" / "private_python"
    candidates = [
        configured,
        configured.parent / f"cpython-{PYTHON_VERSION}-x64",
        home / f"cpython-{PYTHON_VERSION}-x64-astral-20250409",
        home / f"cpython-{PYTHON_VERSION}-x64",
    ]
    return list(dict.fromkeys(candidates))


def _inspect_one(root: Path) -> dict[str, Any]:
    executable = root / "python.exe"

    result: dict[str, Any] = {
        "path": str(executable),
        "version": PYTHON_VERSION,
        "installed": executable.is_file(),
        "ready": False,
    }

    if not executable.is_file():
        return result

    try:
        check = subprocess.run(
            [
                str(executable),
                "-I",
                "-c",
                (
                    "import sys, venv, ensurepip; "
                    "assert sys.version_info[:3] == (3, 12, 10); "
                    "assert sys.maxsize > 2**32"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        result["ready"] = check.returncode == 0

        if not result["ready"]:
            result["error"] = (
                check.stderr.strip()
                or f"Python-Pruefung fehlgeschlagen: {check.returncode}"
            )

    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)

    return result


def inspect_runtime(root: Path | None = None) -> dict[str, Any]:
    """Find an existing managed runtime, or check exactly the supplied root.

    An explicit root is important for staging checks during installation.
    """
    if root is not None:
        return _inspect_one(Path(root))

    checked = []
    for candidate in runtime_candidates():
        result = _inspect_one(candidate)
        checked.append(result)
        if result["ready"]:
            result["source"] = "managed_runtime"
            return result

    result = checked[0]
    result["checked_paths"] = [item["path"] for item in checked]
    return result


def install_local_archive(
    package: str | Path,
    expected_sha256: str,
    *,
    confirmed: bool = False,
    target: Path | None = None,
) -> dict[str, Any]:
    """Installiert ein lokal bereitgestelltes ZIP nur nach ausdruecklicher Zustimmung.

    Diese Funktion laedt nichts herunter und startet keinen System-Installer.
    Die Herkunft des Archivs und sein vertrauenswuerdiger SHA256-Wert muessen
    ausserhalb dieser Funktion geprueft werden.
    """
    if not confirmed:
        raise PermissionError("Python-Runtime-Installation muss bestaetigt werden.")

    import importlib.util
    import re

    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("SHA256 muss aus genau 64 Hex-Zeichen bestehen.")

    installer_file = Path(__file__).with_name("portable_installer.py")
    spec = importlib.util.spec_from_file_location(
        "mediahub_python_runtime_portable_installer", installer_file
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Portabler Runtime-Installer nicht verfuegbar.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.install_verified_runtime(
        package=package,
        target=target if target is not None else runtime_root(),
        expected_sha256=expected_sha256,
    )


def install_from_tools_repo(*, confirmed: bool = False, target: Path | None = None) -> dict[str, Any]:
    """Explizit bestaetigter Download aus MediaHub_Tools und sichere Installation."""
    if not confirmed:
        raise PermissionError("Download und Installation muessen bestaetigt werden.")
    import importlib.util

    module_path = Path(__file__).with_name("tools_download.py")
    spec = importlib.util.spec_from_file_location("mediahub_python_tools_download", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Tools-Downloadmodul fehlt.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.download_and_install(confirmed=True, target=target)


class MediaHubPythonRuntimePlugin:
    plugin_id = "mediahub.python_runtime"
    name = "MediaHub Python Runtime"
    version = "0.1.3"

    def health(self) -> dict[str, Any]:
        runtime = inspect_runtime()

        return {
            "plugin_id": self.plugin_id,
            "status": "online" if runtime["ready"] else "not_configured",
            "ready": runtime["ready"],
            "runtime": runtime,
        }

