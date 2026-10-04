"""Provisioning plan for the isolated SmolVLM2 runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from runtime_profiles import runtime_profile


class SmolVLM2ProvisionError(RuntimeError):
    pass


def _run(
    command: list[str],
) -> subprocess.CompletedProcess[str]:

    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def inspect_python(
    python_executable: str | Path,
) -> dict[str, Any]:

    python_path = Path(
        python_executable
    )

    if not python_path.is_file():
        return {
            "available": False,
            "python": str(python_path),
        }

    completed = _run(
        [
            str(python_path),
            "-c",
            (
                "import json,sys,platform;"
                "print(json.dumps({"
                "'version':sys.version.split()[0],"
                "'executable':sys.executable,"
                "'machine':platform.machine(),"
                "'system':platform.system()"
                "}))"
            ),
        ]
    )

    if completed.returncode != 0:
        return {
            "available": False,
            "python": str(python_path),
            "error": completed.stderr.strip(),
        }

    try:
        data = json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "python": str(python_path),
            "error": str(exc),
        }

    return {
        "available": True,
        "python": str(python_path),
        **data,
    }


def inspect_cuda(
    python_executable: str | Path,
) -> dict[str, Any]:

    python_path = Path(
        python_executable
    )

    if not python_path.is_file():
        return {
            "torch": False,
            "cuda_available": False,
        }

    script = r'''
import json

try:
    import torch
except Exception as exc:  # noqa: BLE001
    print(json.dumps({
        "torch": False,
        "cuda_available": False,
        "error": str(exc),
    }))
    raise SystemExit(0)

data = {
    "torch": True,
    "torch_version": str(torch.__version__),
    "cuda_runtime": (
        str(torch.version.cuda)
        if torch.version.cuda
        else None
    ),
    "cuda_available": bool(
        torch.cuda.is_available()
    ),
    "gpu_count": (
        torch.cuda.device_count()
        if torch.cuda.is_available()
        else 0
    ),
    "gpu_name": (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else None
    ),
}

print(json.dumps(data))
'''

    completed = _run(
        [
            str(python_path),
            "-c",
            script,
        ]
    )

    if completed.returncode != 0:
        return {
            "torch": False,
            "cuda_available": False,
            "error": completed.stderr.strip(),
        }

    try:
        return json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "torch": False,
            "cuda_available": False,
            "error": str(exc),
        }


def resolve_backend(
    python_executable: str | Path,
    requested: str = "auto",
) -> str:

    requested = str(
        requested or "auto"
    ).strip().lower()

    profile = runtime_profile(
        requested
    )

    if profile["platform"] == "unsupported":
        raise SmolVLM2ProvisionError(
            "Plattform wird derzeit nicht "
            "unterstuetzt."
        )

    if requested == "cpu":
        if not profile["cpu"]["supported"]:
            raise SmolVLM2ProvisionError(
                "CPU-Runtime wird auf dieser "
                "Plattform nicht unterstuetzt."
            )

        return "cpu"

    if requested == "cuda":
        if not profile["cuda"]["supported"]:
            raise SmolVLM2ProvisionError(
                "CUDA-Runtime wird auf dieser "
                "Plattform nicht unterstuetzt."
            )

        return "cuda"

    cuda = inspect_cuda(
        python_executable
    )

    if (
        profile["cuda"]["supported"]
        and cuda.get(
            "cuda_available",
            False,
        )
    ):
        return "cuda"

    return "cpu"


def provision_plan(
    python_executable: str | Path,
    requested: str = "auto",
) -> dict[str, Any]:

    python_status = inspect_python(
        python_executable
    )

    if not python_status.get(
        "available",
        False,
    ):
        raise SmolVLM2ProvisionError(
            "Private Python ist nicht "
            "verfuegbar."
        )

    profile = runtime_profile(
        requested
    )

    backend = resolve_backend(
        python_executable,
        requested,
    )

    backend_profile = profile[
        backend
    ]

    packages = list(
        backend_profile.get(
            "packages",
            []
        )
    )

    common_packages = list(
        profile.get(
            "common_packages",
            []
        )
    )

    commands = []

    index_url = backend_profile.get(
        "index_url"
    )

    torch_command = [
        str(python_executable),
        "-m",
        "pip",
        "install",
        *packages,
    ]

    if index_url:
        torch_command.extend(
            [
                "--index-url",
                str(index_url),
            ]
        )

    commands.append(
        torch_command
    )

    commands.append(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            *common_packages,
        ]
    )

    return {
        "platform": profile["platform"],
        "requested_backend": requested,
        "selected_backend": backend,
        "python": python_status,
        "runtime": backend_profile,
        "common_packages": common_packages,
        "commands": commands,
        "execute": False,
    }

