"""Managed isolated runtime for SmolVLM2."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any

RUNTIME_NAME = "smolvlm2"

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


def _load_local_module(name: str, filename: str):
    module_path = Path(__file__).resolve().parent / filename

    spec = importlib.util.spec_from_file_location(
        name,
        module_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"SmolVLM2-Modul kann nicht geladen werden: {module_path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def _load_python_runtime_provider():
    return _load_local_module(
        "mediahub_smolvlm2_python_runtime",
        "python_runtime.py",
    )


def _load_python_provisioner():
    return _load_local_module(
        "mediahub_smolvlm2_python_provisioner",
        "python_provisioner.py",
    )


def _load_pip_bootstrap():
    return _load_local_module(
        "mediahub_smolvlm2_pip_bootstrap",
        "pip_bootstrap.py",
    )


def _load_runtime_provisioner():
    return _load_local_module(
        "mediahub_smolvlm2_runtime_provisioner",
        "runtime_provisioner.py",
    )


def mediahub_compute_root() -> Path:
    return (
        Path.home()
        / ".mediahub"
        / "compute_node"
    )


def runtime_root() -> Path:
    override = os.environ.get(
        "MEDIAHUB_COMPUTE_RUNTIME"
    )

    if override:
        return (
            Path(override)
            / "plugin_runtimes"
            / RUNTIME_NAME
        )

    return (
        mediahub_compute_root()
        / "plugin_runtimes"
        / RUNTIME_NAME
    )


def runtime_paths() -> dict[str, Path]:
    root = runtime_root()

    return {
        "root": root,
        "venv": root / "venv",
        "state": root / "state.json",
        "models": root / "models",
        "cache": root / "cache",
    }


def models_root() -> Path:
    """Return the centrally managed SmolVLM2 model root."""

    override = os.environ.get(
        "MEDIAHUB_COMPUTE_RUNTIME"
    )

    if override:
        return (
            Path(override)
            / "runtimes"
            / RUNTIME_NAME
            / "models"
        )

    return (
        mediahub_compute_root()
        / "runtimes"
        / RUNTIME_NAME
        / "models"
    )


def cache_root() -> Path:
    return runtime_paths()["cache"]


def state_path() -> Path:
    return runtime_paths()["state"]


def runtime_base_python() -> Path:
    provider = _load_python_runtime_provider()
    return Path(provider.require_python())


def _python_has_module(
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
                f"0 if importlib.util.find_spec({module!r}) "
                "else 1)"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return completed.returncode == 0


def _venv_python_path() -> Path:
    paths = runtime_paths()

    if os.name == "nt":
        return (
            paths["venv"]
            / "Scripts"
            / "python.exe"
        )

    return (
        paths["venv"]
        / "bin"
        / "python"
    )


def venv_python() -> Path:
    venv_path = _venv_python_path()

    if venv_path.is_file():
        return venv_path

    base_python = runtime_base_python()

    if (
        base_python.is_file()
        and not _python_has_module(
            base_python,
            "venv",
        )
    ):
        raise RuntimeError(
            "Das gefundene Python unterstuetzt keine "
            "isolierte venv-Runtime."
        )

    return venv_path


def private_python() -> Path:
    """Compatibility alias for older SmolVLM2 callers."""
    return venv_python()


def _torch_status(
    python_path: Path,
) -> dict[str, Any]:
    if not _python_has_module(
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
    "cuda_available": bool(torch.cuda.is_available()),
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
    paths = runtime_paths()

    try:
        python_path = venv_python()
        runtime_error = None
    except Exception as exc:  # noqa: BLE001
        python_path = _venv_python_path()
        runtime_error = str(exc)

    packages: dict[str, bool] = {}

    if python_path.is_file():
        for package, module in REQUIRED_MODULES.items():
            packages[package] = _python_has_module(
                python_path,
                module,
            )
    else:
        for package in REQUIRED_MODULES:
            packages[package] = False

    ready = (
        python_path.is_file()
        and all(packages.values())
    )

    return {
        "runtime": RUNTIME_NAME,
        "root": str(paths["root"]),
        "venv_exists": paths["venv"].is_dir(),
        "python": str(python_path),
        "python_exists": python_path.is_file(),
        "packages": packages,
        "torch": _torch_status(python_path),
        "models": str(models_root()),
        "cache": str(paths["cache"]),
        "ready": ready,
        "error": runtime_error,
    }


def create_runtime() -> dict[str, Any]:
    paths = runtime_paths()

    paths["root"].mkdir(
        parents=True,
        exist_ok=True,
    )
    models_root().mkdir(
        parents=True,
        exist_ok=True,
    )
    paths["cache"].mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        base_python = runtime_base_python()
    except RuntimeError:
        provisioner = _load_python_provisioner()
        provisioned = (
            provisioner.provision_private_python()
        )
        base_python = Path(
            provisioned["python"]
        )

    if not base_python.is_file():
        raise RuntimeError(
            "Kein kompatibles SmolVLM2-Runtime-Python vorhanden."
        )

    traditional_venv_python = (
        _venv_python_path()
    )

    if traditional_venv_python.is_file():
        python_path = traditional_venv_python
        runtime_mode = "venv"

    elif _python_has_module(
        base_python,
        "venv",
    ):
        subprocess.run(
            [
                str(base_python),
                "-m",
                "venv",
                str(paths["venv"]),
            ],
            check=True,
        )

        python_path = traditional_venv_python
        runtime_mode = "venv"

    else:
        raise RuntimeError(
            "Das gefundene Python unterstuetzt keine "
            "isolierte venv-Runtime. Die SmolVLM2-"
            "Abhaengigkeiten werden nicht in das "
            "System-Python installiert."
        )

    if not python_path.is_file():
        raise RuntimeError(
            "SmolVLM2-Runtime-Python wurde nicht erstellt."
        )

    state = {
        "runtime": RUNTIME_NAME,
        "mode": runtime_mode,
        "created_with": str(base_python),
        "python": str(python_path),
        "models": str(models_root()),
        "cache": str(paths["cache"]),
    }

    paths["state"].write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return inspect_runtime()


def ensure_directories() -> dict[str, Any]:
    """Compatibility wrapper for existing callers."""
    return create_runtime()


def install_dependencies(
    requested_backend: str = "auto",
) -> dict[str, Any]:
    paths = runtime_paths()
    status = create_runtime()

    python_path = Path(
        status["python"]
    )

    pip_bootstrap = _load_pip_bootstrap()
    pip_status = pip_bootstrap.inspect_pip(
        python_path
    )

    if not pip_status.get("pip"):
        bootstrap_file = (
            paths["root"]
            / "get-pip.py"
        )

        pip_bootstrap.download_get_pip(
            bootstrap_file
        )

        try:
            pip_bootstrap.bootstrap_pip(
                python_path,
                bootstrap_file,
            )
        finally:
            if bootstrap_file.exists():
                bootstrap_file.unlink()

    subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        ],
        check=True,
    )

    provisioner = _load_runtime_provisioner()
    plan = provisioner.provision_plan(
        python_path,
        requested_backend,
    )

    for command in plan.get("commands", []):
        if command:
            subprocess.run(
                [str(part) for part in command],
                check=True,
            )

    status = inspect_runtime()

    if not status["ready"]:
        raise RuntimeError(
            "SmolVLM2-Runtime wurde installiert, "
            "ist aber nicht bereit."
        )

    status["selected_backend"] = (
        plan.get("selected_backend")
    )
    status["platform"] = plan.get("platform")

    return status
