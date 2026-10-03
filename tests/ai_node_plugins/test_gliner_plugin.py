"""Tests for the MediaHub GLiNER AI-Node plugin."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PLUGIN_DIR = (
    Path(__file__).resolve().parents[2]
    / "ai_node_plugins"
    / "gliner"
)
PLUGIN_FILE = PLUGIN_DIR / "plugin.py"


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location(
        "mediahub_gliner_plugin_test",
        PLUGIN_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "GLiNER plugin module could not be loaded."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _disable_runtime_installation(module):
    """Prevent handler tests from changing the real plugin runtime."""

    calls = []

    def ensure_runtime(
        *,
        capabilities,
        requested_profile="auto",
    ):
        calls.append(
            {
                "capabilities": capabilities,
                "requested_profile": requested_profile,
            }
        )

        return {
            "ready": True,
            "installation_required": False,
        }

    module._ensure_runtime = ensure_runtime

    return calls


class _WorkerRegistryStub:
    def __init__(self):
        self.registered = {}

    def register(
        self,
        *,
        worker_id,
        name,
        job_types,
        handler,
        metadata=None,
        **kwargs,
    ):
        self.registered[worker_id] = {
            "worker_id": worker_id,
            "name": name,
            "job_types": job_types,
            "handler": handler,
            "metadata": metadata or {},
        }



def test_ensure_runtime_cuda_node_with_cpu_runtime_installs_cuda():
    module = _load_plugin_module()

    capabilities = {
        "accelerators": [
            {
                "kind": "gpu",
                "vendor": "NVIDIA",
                "name": "Test GPU",
                "backend_family": ["cuda"],
            }
        ],
    }

    module._RUNTIME_MANAGER.inspect_runtime = (
        lambda: {
            "ready": True,
            "mode": "isolated_target",
            "python": "test-python",
            "packages_path": "test-packages",
        }
    )

    module._RUNTIME_MANAGER.inspect_acceleration = (
        lambda: {
            "torch_available": True,
            "torch_version": "2.14.0+cpu",
            "cuda_built": False,
            "cuda_available": False,
        }
    )

    calls = []

    def fake_install_dependencies(
        root=None,
        *,
        profile="auto",
        capabilities=None,
    ):
        calls.append(
            {
                "root": root,
                "profile": profile,
                "capabilities": capabilities,
            }
        )

        return {
            "ready": True,
            "mode": "isolated_target",
            "python": "test-python",
            "packages_path": "test-packages",
            "install_profile": {
                "selected": profile,
            },
            "acceleration": {
                "cuda_available": True,
            },
        }

    module._RUNTIME_MANAGER.install_dependencies = (
        fake_install_dependencies
    )

    result = module._ensure_runtime(
        capabilities=capabilities,
    )

    assert result["installation_required"] is True

    assert len(calls) == 1
    assert calls[0]["profile"] == "cuda"
    assert calls[0]["capabilities"] == capabilities


def test_ensure_runtime_cuda_runtime_does_not_install():
    module = _load_plugin_module()

    capabilities = {
        "accelerators": [
            {
                "kind": "gpu",
                "vendor": "NVIDIA",
                "name": "Test GPU",
                "backend_family": ["cuda"],
            }
        ],
    }

    module._RUNTIME_MANAGER.inspect_runtime = (
        lambda: {
            "ready": True,
            "mode": "isolated_target",
            "python": "test-python",
            "packages_path": "test-packages",
        }
    )

    module._RUNTIME_MANAGER.inspect_acceleration = (
        lambda: {
            "torch_available": True,
            "torch_version": "2.14.0+cu126",
            "cuda_built": True,
            "cuda_version": "12.6",
            "cuda_available": True,
            "cuda_device_count": 1,
        }
    )

    def forbidden_install(*args, **kwargs):
        raise AssertionError(
            "CUDA-Runtime ist bereits bereit; "
            "Installation darf nicht laufen."
        )

    module._RUNTIME_MANAGER.install_dependencies = (
        forbidden_install
    )

    result = module._ensure_runtime(
        capabilities=capabilities,
    )

    assert result["installation_required"] is False
    assert (
        result["install_profile"]["selected"]
        == "cuda"
    )
    assert result["acceleration"]["cuda_available"] is True


def test_ensure_runtime_cpu_node_with_cpu_runtime_does_not_install():
    module = _load_plugin_module()

    capabilities = {
        "accelerators": [],
    }

    module._RUNTIME_MANAGER.inspect_runtime = (
        lambda: {
            "ready": True,
            "mode": "isolated_target",
            "python": "test-python",
            "packages_path": "test-packages",
        }
    )

    module._RUNTIME_MANAGER.inspect_acceleration = (
        lambda: {
            "torch_available": True,
            "torch_version": "2.14.0+cpu",
            "cuda_built": False,
            "cuda_available": False,
        }
    )

    def forbidden_install(*args, **kwargs):
        raise AssertionError(
            "CPU-Runtime ist bereits bereit; "
            "Installation darf nicht laufen."
        )

    module._RUNTIME_MANAGER.install_dependencies = (
        forbidden_install
    )

    result = module._ensure_runtime(
        capabilities=capabilities,
    )

    assert result["installation_required"] is False
    assert (
        result["install_profile"]["selected"]
        == "cpu"
    )
    assert result["acceleration"]["cuda_available"] is False



def test_gliner_worker_registers_and_executes_mock_job():
    module = _load_plugin_module()
    ensure_calls = _disable_runtime_installation(module)
    workers = _WorkerRegistryStub()

    module._RUNTIME_MANAGER.inspect_acceleration = (
        lambda: {
            "torch_available": True,
            "torch_version": "test+cu126",
            "cuda_built": True,
            "cuda_version": "12.6",
            "cuda_available": True,
            "cuda_device_count": 1,
            "devices": [
                {
                    "index": 0,
                    "name": "Test GPU",
                    "capability": [8, 6],
                }
            ],
            "error": None,
        }
    )

    context = {
        "workers": workers,
        "plugin_id": "mediahub.gliner",
        "plugin_version": "0.1.0",
        "capabilities": {
            "accelerators": [
                {
                    "kind": "gpu",
                    "vendor": "NVIDIA",
                    "name": "Test GPU",
                    "backend_family": ["cuda"],
                }
            ],
        },
    }

    plugin = module.MediaHubGLiNERPlugin()
    plugin.register(context)

    assert "mediahub.gliner.worker" in workers.registered

    worker = workers.registered[
        "mediahub.gliner.worker"
    ]

    assert worker["job_types"] == [
        "text_entity_extraction"
    ]

    request = {
        "payload": {
            "text": (
                "NCIS mit Leroy Jethro Gibbs "
                "spielt in Washington."
            ),
            "options": {
                "mock": True,
                "mock_entities": [
                    {
                        "text": "NCIS",
                        "label": "title",
                        "score": 0.99,
                        "start": 0,
                        "end": 4,
                    },
                    {
                        "text": "Leroy Jethro Gibbs",
                        "label": "person",
                        "score": 0.98,
                        "start": 9,
                        "end": 27,
                    },
                ],
            },
        },
        "execution": {
            "mode": "auto",
            "cpu_threads": 4,
        },
    }

    result = worker["handler"](request)

    assert result["status"] == "completed"
    assert result["engine"] == "mock"
    assert result["execution"]["backend"] == "cuda"

    entities = result["analysis"]["entities"]

    assert len(entities) == 2
    assert entities[0]["text"] == "NCIS"
    assert entities[0]["label"] == "title"
    assert entities[1]["text"] == "Leroy Jethro Gibbs"
    assert entities[1]["label"] == "person"
    assert len(ensure_calls) == 1


def test_gliner_cuda_node_with_cpu_runtime_uses_cpu():
    module = _load_plugin_module()
    ensure_calls = _disable_runtime_installation(module)
    workers = _WorkerRegistryStub()

    module._RUNTIME_MANAGER.inspect_acceleration = (
        lambda: {
            "torch_available": True,
            "torch_version": "2.14.0+cpu",
            "cuda_built": False,
            "cuda_version": None,
            "cuda_available": False,
            "cuda_device_count": 0,
            "devices": [],
            "error": None,
        }
    )

    context = {
        "workers": workers,
        "plugin_id": "mediahub.gliner",
        "plugin_version": "0.1.0",
        "capabilities": {
            "accelerators": [
                {
                    "kind": "gpu",
                    "vendor": "NVIDIA",
                    "name": "Test GPU",
                    "backend_family": ["cuda"],
                }
            ],
        },
    }

    plugin = module.MediaHubGLiNERPlugin()
    plugin.register(context)

    worker = workers.registered[
        "mediahub.gliner.worker"
    ]

    result = worker["handler"](
        {
            "payload": {
                "text": "NCIS",
                "options": {
                    "mock": True,
                },
            },
            "execution": {
                "mode": "auto",
                "cpu_threads": 4,
            },
        }
    )

    assert result["status"] == "completed"
    assert result["execution"]["backend"] == "cpu"
    assert result["execution"]["cpu_threads"] == 4
    assert len(ensure_calls) == 1


def test_gliner_auto_execution_falls_back_to_cpu():
    module = _load_plugin_module()
    ensure_calls = _disable_runtime_installation(module)
    workers = _WorkerRegistryStub()

    context = {
        "workers": workers,
        "plugin_id": "mediahub.gliner",
        "plugin_version": "0.1.0",
        "capabilities": {
            "accelerators": [],
        },
    }

    plugin = module.MediaHubGLiNERPlugin()
    plugin.register(context)

    worker = workers.registered[
        "mediahub.gliner.worker"
    ]

    result = worker["handler"](
        {
            "payload": {
                "text": "NCIS",
                "options": {
                    "mock": True,
                },
            },
            "execution": {
                "mode": "auto",
                "cpu_threads": 2,
            },
        }
    )

    assert result["status"] == "completed"
    assert result["execution"]["backend"] == "cpu"
    assert result["execution"]["cpu_threads"] == 2
    assert len(ensure_calls) == 1


def test_runtime_runner_requires_packages_path():
    """Runner must reject requests without the isolated package path."""

    import json
    import subprocess

    runner = PLUGIN_DIR / "runtime_runner.py"

    request = {
        "text": "NCIS",
        "execution": {
            "mode": "cpu",
            "backend": "cpu",
            "cpu_threads": 2,
        },
        "options": {
            "mock": True,
        },
    }

    process = subprocess.run(
        [
            sys.executable,
            str(runner),
        ],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 1

    response = json.loads(process.stdout)

    assert response["ok"] is False
    assert (
        response["error"]["type"]
        == "RuntimeError"
    )
    assert (
        "packages_path"
        in response["error"]["message"]
    )


def test_runtime_runner_forwards_cuda_execution(
    tmp_path,
):
    """Runner must forward the selected CUDA backend to the engine."""

    import json
    import subprocess

    runner = PLUGIN_DIR / "runtime_runner.py"

    fake_plugin = tmp_path / "plugin"
    fake_plugin.mkdir()

    fake_packages = tmp_path / "packages"
    fake_packages.mkdir()

    fake_runner = fake_plugin / "runtime_runner.py"
    fake_engine = fake_plugin / "engine.py"

    fake_runner.write_text(
        runner.read_text(
            encoding="utf-8-sig"
        ),
        encoding="utf-8",
    )

    fake_engine.write_text(
        """
def analyze_text(*, text, execution, options):
    return {
        "engine": "test-engine",
        "text": text,
        "execution": execution,
        "options": options,
    }
""".lstrip(),
        encoding="utf-8",
    )

    request = {
        "packages_path": str(
            fake_packages
        ),
        "text": "NCIS",
        "execution": {
            "mode": "gpu",
            "backend": "cuda",
            "cpu_threads": 4,
        },
        "options": {
            "model": "test-model",
            "threshold": 0.30,
        },
    }

    process = subprocess.run(
        [
            sys.executable,
            str(fake_runner),
        ],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0, (
        process.stderr
        or process.stdout
    )

    response = json.loads(
        process.stdout
    )

    assert response["ok"] is True

    result = response["result"]

    assert result["engine"] == "test-engine"
    assert result["text"] == "NCIS"

    assert (
        result["execution"]["mode"]
        == "gpu"
    )
    assert (
        result["execution"]["backend"]
        == "cuda"
    )
    assert (
        result["execution"]["cpu_threads"]
        == 4
    )

    assert (
        result["options"]["model"]
        == "test-model"
    )
    assert (
        result["options"]["threshold"]
        == 0.30
    )
