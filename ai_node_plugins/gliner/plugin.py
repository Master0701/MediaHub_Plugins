"""MediaHub GLiNER worker plugin."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_PLUGIN_DIR = Path(__file__).resolve().parent

_RUNTIME_MANAGER_FILE = (
    _PLUGIN_DIR / "runtime_manager.py"
)

_RUNTIME_BRIDGE_FILE = (
    _PLUGIN_DIR / "runtime_bridge.py"
)

_RUNTIME_RUNNER_FILE = (
    _PLUGIN_DIR / "runtime_runner.py"
)

_ENGINE_FILE = (
    _PLUGIN_DIR / "engine.py"
)


def _load_module(
    name: str,
    path: Path,
):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "GLiNER-Modul kann nicht geladen werden: "
            f"{path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


_RUNTIME_MANAGER = _load_module(
    "mediahub_gliner_runtime_manager",
    _RUNTIME_MANAGER_FILE,
)

_RUNTIME_BRIDGE = _load_module(
    "mediahub_gliner_runtime_bridge",
    _RUNTIME_BRIDGE_FILE,
)

_ENGINE = _load_module(
    "mediahub_gliner_engine",
    _ENGINE_FILE,
)


def _capabilities(
    context: dict[str, Any],
) -> dict[str, Any]:
    provider = context.get(
        "capabilities_provider"
    )

    if callable(provider):
        value = provider()

        if isinstance(value, dict):
            return value

    value = context.get(
        "capabilities"
    )

    if isinstance(value, dict):
        return value

    return {}


def _choose_execution(
    request: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    requested = request.get("execution")

    if isinstance(requested, dict):
        selected = dict(requested)
    else:
        selected = {}

    mode = str(
        selected.get(
            "mode",
            "auto",
        )
    ).strip().lower()

    capabilities = _capabilities(context)

    node_cuda_available = False

    accelerators = capabilities.get(
        "accelerators"
    )

    if isinstance(accelerators, list):
        for accelerator in accelerators:
            if not isinstance(
                accelerator,
                dict,
            ):
                continue

            families = accelerator.get(
                "backend_family"
            )

            if (
                isinstance(families, list)
                and "cuda" in families
            ):
                node_cuda_available = True
                break

    runtime_acceleration = (
        _RUNTIME_MANAGER.inspect_acceleration()
    )

    runtime_cuda_available = bool(
        runtime_acceleration.get(
            "cuda_available"
        )
    )

    cuda_available = (
        node_cuda_available
        and runtime_cuda_available
    )

    if mode == "cpu":
        backend = "cpu"

    elif mode == "gpu":
        backend = (
            "cuda"
            if cuda_available
            else "cpu"
        )

    else:
        backend = (
            "cuda"
            if cuda_available
            else "cpu"
        )

    return {
        "mode": mode,
        "backend": backend,
        "cpu_threads": int(
            selected.get(
                "cpu_threads",
                4,
            )
        ),
    }


def _runtime_status() -> dict[str, Any]:
    return _RUNTIME_MANAGER.inspect_runtime()


def _ensure_runtime(
    *,
    capabilities: dict[str, Any] | None,
    requested_profile: str = "auto",
) -> dict[str, Any]:
    """Ensure that the required GLiNER runtime profile is available."""

    selection = _RUNTIME_MANAGER.select_install_profile(
        requested=requested_profile,
        capabilities=capabilities,
    )

    selected = str(
        selection["selected"]
    )

    status = _RUNTIME_MANAGER.inspect_runtime()
    acceleration = _RUNTIME_MANAGER.inspect_acceleration()

    runtime_ready = bool(
        status.get("ready")
    )

    if selected == "cuda":
        profile_ready = bool(
            acceleration.get("cuda_available")
        )
    else:
        profile_ready = runtime_ready

    if runtime_ready and profile_ready:
        return {
            **status,
            "install_profile": selection,
            "acceleration": acceleration,
            "installation_required": False,
        }

    installed = _RUNTIME_MANAGER.install_dependencies(
        profile=selected,
        capabilities=capabilities,
    )

    return {
        **installed,
        "installation_required": True,
    }


def _engine_metadata() -> dict[str, Any]:
    status = _runtime_status()

    return {
        "engine": "gliner",
        "available": bool(
            status.get("ready")
        ),
        "runtime": status.get(
            "mode"
        ),
        "isolated": True,
    }


def _run_analysis(
    *,
    text: str,
    execution: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    if options.get("mock"):
        return _ENGINE.analyze_text(
            text=text,
            execution=execution,
            options=options,
        )

    status = _runtime_status()

    if not status.get("ready"):
        raise RuntimeError(
            "Die isolierte GLiNER-Runtime "
            "ist nicht bereit. "
            f"Status: {status}"
        )

    return _RUNTIME_BRIDGE.run_analysis(
        runtime_python=status["python"],
        packages_path=status["packages_path"],
        runner_path=_RUNTIME_RUNNER_FILE,
        text=text,
        execution=execution,
        options=options,
    )

def create_handler(
    context: dict[str, Any],
):
    def handler(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(
            request.get("payload")
            or {}
        )

        text = str(
            payload.get("text")
            or ""
        ).strip()

        if not text:
            raise ValueError(
                "GLiNER-Job benoetigt payload.text."
            )

        options = dict(
            payload.get("options")
            or {}
        )

        capabilities = _capabilities(
            context
        )

        _ensure_runtime(
            capabilities=capabilities,
        )

        execution = _choose_execution(
            request,
            context,
        )

        result = _run_analysis(
            text=text,
            execution=execution,
            options=options,
        )

        return {
            "status": "completed",
            "engine": result[
                "engine"
            ],
            "execution": execution,
            "analysis": result,
        }

    return handler


def register(
    context: dict[str, Any],
) -> None:
    workers = context["workers"]

    workers.register(
        worker_id="mediahub.gliner.worker",
        name="MediaHub GLiNER Worker",
        job_types=[
            "text_entity_extraction"
        ],
        handler=create_handler(
            context
        ),
        metadata={
            "plugin_id": context[
                "plugin_id"
            ],
            "plugin_version": context[
                "plugin_version"
            ],
            "execution_modes": [
                "auto",
                "cpu",
                "gpu",
            ],
            "capabilities": [
                "text_entity_extraction",
                "semantic_text_analysis",
            ],
            "engine": _engine_metadata(),
        },
    )


class MediaHubGLiNERPlugin:
    """Shared MediaHub AI-/Compute-Node GLiNER plugin."""

    def register(
        self,
        context: dict[str, Any],
    ) -> None:
        register(context)
