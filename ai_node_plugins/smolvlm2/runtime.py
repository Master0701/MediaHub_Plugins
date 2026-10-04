"""Managed runtime inspection for SmolVLM2."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

RUNTIME_NAME = "smolvlm2"

PRIVATE_PYTHON_VERSION = "3.12.10"

REQUIRED_MODULES = {
    "torch": "torch",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "accelerate": "accelerate",
    "safetensors": "safetensors",
    "huggingface_hub": "huggingface_hub",
    "Pillow": "PIL",
    "num2words": "num2words",
    "numpy": "numpy",
}


def mediahub_compute_root() -> Path:
    return (
        Path.home()
        / ".mediahub"
        / "compute_node"
    )


def runtime_root() -> Path:
    return (
        mediahub_compute_root()
        / "runtimes"
        / RUNTIME_NAME
    )


def models_root() -> Path:
    return runtime_root() / "models"


def cache_root() -> Path:
    return runtime_root() / "cache"


def state_path() -> Path:
    return runtime_root() / "runtime.json"


def private_python_root() -> Path:
    if os.name == "nt":
        name = (
            "cpython-"
            + PRIVATE_PYTHON_VERSION
            + "-x64"
        )
    else:
        name = (
            "cpython-"
            + PRIVATE_PYTHON_VERSION
        )

    return (
        mediahub_compute_root()
        / "private_python"
        / name
    )


def private_python() -> Path:
    root = private_python_root()

    if os.name == "nt":
        return root / "python.exe"

    return root / "bin" / "python3"


def _module_available(
    python_path: Path,
    module: str,
) -> bool:
    if not python_path.is_file():
        return False

    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "import importlib.util,sys;"
                "sys.exit("
                "0 if importlib.util.find_spec("
                f"{module!r}"
                ") else 1)"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return completed.returncode == 0


def _torch_status(
    python_path: Path,
) -> dict[str, Any]:
    if not _module_available(
        python_path,
        "torch",
    ):
        return {
            "available": False,
            "cuda_available": False,
        }

    script = r'''
import json
import torch

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

    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            script,
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        return {
            "available": True,
            "cuda_available": False,
            "error": (
                completed.stderr or ""
            ).strip(),
        }

    try:
        return json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "available": True,
            "cuda_available": False,
            "error": str(exc),
        }


def inspect_runtime() -> dict[str, Any]:
    python_path = private_python()

    packages = {}

    for package, module in (
        REQUIRED_MODULES.items()
    ):
        packages[package] = (
            _module_available(
                python_path,
                module,
            )
        )

    ready = (
        python_path.is_file()
        and all(packages.values())
    )

    return {
        "runtime": RUNTIME_NAME,
        "root": str(runtime_root()),
        "python": str(python_path),
        "python_exists": (
            python_path.is_file()
        ),
        "packages": packages,
        "torch": _torch_status(
            python_path
        ),
        "models": str(models_root()),
        "cache": str(cache_root()),
        "ready": ready,
    }


def ensure_directories() -> dict[str, Any]:
    runtime_root().mkdir(
        parents=True,
        exist_ok=True,
    )

    models_root().mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_root().mkdir(
        parents=True,
        exist_ok=True,
    )

    state = {
        "runtime": RUNTIME_NAME,
        "python": str(private_python()),
        "models": str(models_root()),
        "cache": str(cache_root()),
    }

    state_path().write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return inspect_runtime()

