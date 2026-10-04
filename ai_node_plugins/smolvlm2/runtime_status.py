"""Status inspection for the isolated SmolVLM2 runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from runtime_manifest import runtime_manifest
from runtime_profiles import runtime_profile

REQUIRED_COMMON_MODULES = (
    "transformers",
    "accelerate",
    "safetensors",
    "huggingface_hub",
    "PIL",
    "num2words",
    "numpy",
)

REQUIRED_TORCH_MODULES = (
    "torch",
    "torchvision",
)


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


def inspect_modules(
    python_executable: str | Path,
) -> dict[str, Any]:

    python_path = Path(python_executable)

    if not python_path.is_file():
        return {
            "available": False,
            "python": str(python_path),
            "modules": {},
        }

    modules = (
        *REQUIRED_TORCH_MODULES,
        *REQUIRED_COMMON_MODULES,
    )

    script = f"""
import importlib.util
import json

modules = {modules!r}

result = {{}}

for name in modules:
    result[name] = (
        importlib.util.find_spec(name)
        is not None
    )

print(json.dumps(result))
"""

    completed = _run(
        [
            str(python_path),
            "-c",
            script,
        ]
    )

    if completed.returncode != 0:
        return {
            "available": False,
            "python": str(python_path),
            "modules": {},
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
            "modules": {},
            "error": str(exc),
        }

    return {
        "available": True,
        "python": str(python_path),
        "modules": data,
    }


def inspect_torch(
    python_executable: str | Path,
) -> dict[str, Any]:

    python_path = Path(python_executable)

    if not python_path.is_file():
        return {
            "available": False,
            "cuda_available": False,
        }

    script = r'''
import json

try:
    import torch
except Exception as exc:  # noqa: BLE001
    print(json.dumps({
        "available": False,
        "cuda_available": False,
        "error": str(exc),
    }))
    raise SystemExit(0)

data = {
    "available": True,
    "version": str(torch.__version__),
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
            "available": False,
            "cuda_available": False,
            "error": completed.stderr.strip(),
        }

    try:
        return json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "cuda_available": False,
            "error": str(exc),
        }


def runtime_status(
    python_executable: str | Path,
    requested_backend: str = "auto",
) -> dict[str, Any]:

    manifest = runtime_manifest()

    try:
        profile = runtime_profile(
            requested_backend
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ready": False,
            "error": str(exc),
            "manifest": manifest,
        }

    modules = inspect_modules(
        python_executable
    )

    torch = inspect_torch(
        python_executable
    )

    module_states = modules.get(
        "modules",
        {},
    )

    missing = [
        name
        for name, available
        in module_states.items()
        if not available
    ]

    if not modules.get("available"):
        missing = list(
            REQUIRED_TORCH_MODULES
            + REQUIRED_COMMON_MODULES
        )

    selected_backend = "cpu"

    if (
        requested_backend == "cuda"
        or (
            requested_backend == "auto"
            and torch.get(
                "cuda_available",
                False,
            )
        )
    ):
        selected_backend = "cuda"

    backend_supported = bool(
        profile.get(
            selected_backend,
            {},
        ).get(
            "supported",
            False,
        )
    )

    ready = (
        modules.get("available", False)
        and not missing
        and torch.get("available", False)
        and backend_supported
    )

    if (
        selected_backend == "cuda"
        and not torch.get(
            "cuda_available",
            False,
        )
    ):
        ready = False

    return {
        "ready": ready,
        "requested_backend": requested_backend,
        "selected_backend": selected_backend,
        "backend_supported": backend_supported,
        "missing_modules": missing,
        "python": str(python_executable),
        "modules": modules,
        "torch": torch,
        "platform_profile": profile,
        "manifest": manifest,
    }


