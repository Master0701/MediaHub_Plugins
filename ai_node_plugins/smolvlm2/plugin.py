"""MediaHub SmolVLM2 Compute-Node plugin."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).resolve().parent


def _load_local_module(
    module_name: str,
    filename: str,
):
    module_path = PLUGIN_DIR / filename

    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Lokales SmolVLM2-Modul kann nicht geladen werden: "
            f"{module_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


_EXECUTION = _load_local_module(
    "mediahub_smolvlm2_execution",
    "execution.py",
)

_MODEL_MANAGER = _load_local_module(
    "mediahub_smolvlm2_model_manager",
    "model_manager.py",
)

_RUNTIME = _load_local_module(
    "mediahub_smolvlm2_runtime",
    "runtime.py",
)

_RUNTIME_BRIDGE = _load_local_module(
    "mediahub_smolvlm2_runtime_bridge",
    "runtime_bridge.py",
)

_RUNTIME_MANIFEST = _load_local_module(
    "runtime_manifest",
    "runtime_manifest.py",
)

_RUNTIME_PROFILES = _load_local_module(
    "runtime_profiles",
    "runtime_profiles.py",
)

_RUNTIME_STATUS = _load_local_module(
    "mediahub_smolvlm2_runtime_status",
    "runtime_status.py",
)

select_execution = _EXECUTION.select_execution
resolve_model_path = _MODEL_MANAGER.resolve_model_path
models_root = _RUNTIME.models_root
private_python = _RUNTIME.private_python

SmolVLM2RuntimeBridgeError = (
    _RUNTIME_BRIDGE.SmolVLM2RuntimeBridgeError
)
run_analysis = _RUNTIME_BRIDGE.run_analysis

runtime_status = _RUNTIME_STATUS.runtime_status


WORKER_ID = "mediahub.smolvlm2.worker"

JOB_TYPES = [
    "vision_analysis",
    "video_frame_analysis",
]


RUNTIME_RUNNER = PLUGIN_DIR / "runtime_runner.py"


def _has_gpu(
    capabilities: dict[str, Any],
) -> bool:
    for accelerator in capabilities.get(
        "accelerators",
        [],
    ):
        if (
            accelerator.get("kind") == "gpu"
            and accelerator.get("detected") is True
        ):
            return True

    return False


def _job_input_path(
    job: dict[str, Any],
) -> str | None:
    """Resolve an input image/frame path from a node job."""

    candidates = (
        job.get("input_path"),
        job.get("path"),
        job.get("file_path"),
    )

    payload = job.get("payload")

    if isinstance(payload, dict):
        candidates += (
            payload.get("input_path"),
            payload.get("path"),
            payload.get("file_path"),
        )

    for candidate in candidates:
        if candidate:
            return str(candidate)

    return None


def _job_options(
    job: dict[str, Any],
) -> dict[str, Any]:
    options: dict[str, Any] = {}

    direct_options = job.get("options")

    if isinstance(direct_options, dict):
        options.update(direct_options)

    payload = job.get("payload")

    if isinstance(payload, dict):
        payload_options = payload.get("options")

        if isinstance(payload_options, dict):
            options.update(payload_options)

    return options


def _requested_backend(
    job: dict[str, Any],
) -> str:
    options = _job_options(job)

    backend = (
        options.get("backend")
        or job.get("backend")
        or "auto"
    )

    return str(backend)


def _handle_job(
    job: dict[str, Any],
) -> dict[str, Any]:
    job_type = str(
        job.get("job_type") or ""
    )

    if job_type not in JOB_TYPES:
        return {
            "status": "unsupported_job_type",
            "job_type": job_type,
            "message": (
                "Nicht unterstuetzter "
                "SmolVLM2-Jobtyp."
            ),
        }

    input_path_value = _job_input_path(job)

    if not input_path_value:
        return {
            "status": "invalid_input",
            "job_type": job_type,
            "message": (
                "Kein input_path fuer "
                "SmolVLM2 angegeben."
            ),
        }

    input_path = Path(input_path_value)

    if not input_path.is_file():
        return {
            "status": "input_not_found",
            "job_type": job_type,
            "input_path": str(input_path),
            "message": (
                "Eingabedatei wurde nicht gefunden."
            ),
        }

    requested_backend = _requested_backend(job)

    try:
        execution = select_execution(
            requested_backend
        )
    except ValueError as exc:
        return {
            "status": "invalid_backend",
            "job_type": job_type,
            "message": str(exc),
        }

    runtime_python = private_python()

    status = runtime_status(
        runtime_python,
        requested_backend,
    )

    if not status.get("ready", False):
        return {
            "status": "runtime_not_installed",
            "job_type": job_type,
            "runtime_python": str(runtime_python),
            "requested_backend": requested_backend,
            "runtime_status": status,
            "message": (
                "Die SmolVLM2-Runtime ist nicht "
                "installiert oder nicht bereit."
            ),
        }

    try:
        model_path = resolve_model_path(
            models_root()
        )
    except RuntimeError as exc:
        return {
            "status": "model_not_installed",
            "job_type": job_type,
            "tool_id": "smolvlm2-model",
            "message": str(exc),
        }

    options = _job_options(job)

    # The model is centrally managed by MediaHub Tools.
    # Never let the runtime silently download another copy.
    options["model_path"] = str(model_path)
    options["local_files_only"] = True

    try:
        result = run_analysis(
            runtime_python=runtime_python,
            runner_path=RUNTIME_RUNNER,
            job_type=job_type,
            input_path=input_path,
            execution=execution,
            options=options,
        )
    except SmolVLM2RuntimeBridgeError as exc:
        return {
            "status": "runtime_error",
            "job_type": job_type,
            "message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "job_type": job_type,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "status": "ok",
        "job_type": job_type,
        "model_path": str(model_path),
        "execution": execution,
        "result": result,
    }


def register(
    context: dict[str, Any],
) -> None:
    workers = context["workers"]

    capabilities = context.get(
        "capabilities",
        {},
    )

    gpu_available = _has_gpu(
        capabilities
    )

    workers.register(
        worker_id=WORKER_ID,
        name="MediaHub SmolVLM2 Vision",
        job_types=JOB_TYPES,
        handler=_handle_job,
        enabled=True,
        healthy=True,
        metadata={
            "plugin_id": context.get(
                "plugin_id"
            ),
            "plugin_version": context.get(
                "plugin_version"
            ),
            "engine": "smolvlm2",
            "runtime": "isolated",
            "model_loaded": False,
            "model_tool_id": "smolvlm2-model",
            "gpu_available": gpu_available,
            "preferred_execution": (
                "gpu"
                if gpu_available
                else "cpu"
            ),
        },
    )


class SmolVLM2Plugin:
    """Gemeinsamer Entrypoint fuer AI Node und Windows Compute Node."""

    def register(self, context):
        return register(context)

