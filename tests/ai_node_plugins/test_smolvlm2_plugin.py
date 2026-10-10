from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "ai_node_plugins" / "smolvlm2"


def _load_module(name: str, filename: str):
    path = PLUGIN_DIR / filename

    sys.path.insert(0, str(PLUGIN_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, path)

        if spec is None or spec.loader is None:
            raise RuntimeError(f"Modul kann nicht geladen werden: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(PLUGIN_DIR))
        except ValueError:
            pass


def test_plugin_manifest():
    manifest = json.loads(
        (PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8-sig")
    )

    assert manifest["id"] == "mediahub.smolvlm2"
    assert manifest["version"] == "0.1.1"
    assert manifest["type"] == "model"

    assert "raspberry_pi" in manifest["targets"]
    assert "windows_compute" in manifest["targets"]

    assert "vision_analysis" in manifest["capabilities"]
    assert "video_frame_analysis" in manifest["capabilities"]

    assert manifest["runtime"]["isolated"] is True
    assert manifest["runtime"]["model_storage"] == "mediahub_tools"
    assert manifest["runtime"]["models_bundled"] is False
    assert manifest["runtime"]["model_tool_id"] == "smolvlm2-model"


def test_model_directory_detects_missing_files(tmp_path):
    module = _load_module(
        "test_smolvlm2_model_manager_missing",
        "model_manager.py",
    )

    model = tmp_path / "model"
    model.mkdir()

    status = module.inspect_model_directory(model)

    assert status["exists"] is True
    assert status["ready"] is False
    assert "model.safetensors" in status["missing_files"]
    assert "config.json" in status["missing_files"]


def test_model_directory_accepts_complete_model(tmp_path):
    module = _load_module(
        "test_smolvlm2_model_manager_complete",
        "model_manager.py",
    )

    model = tmp_path / "model"
    model.mkdir()

    required = (
        "added_tokens.json",
        "chat_template.json",
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "processor_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    )

    for filename in required:
        (model / filename).write_bytes(b"test")

    status = module.inspect_model_directory(model)

    assert status["exists"] is True
    assert status["ready"] is True
    assert status["missing_files"] == []


def test_resolve_model_path_rejects_incomplete_model(tmp_path):
    module = _load_module(
        "test_smolvlm2_model_manager_resolve",
        "model_manager.py",
    )

    with pytest.raises(RuntimeError):
        module.resolve_model_path(tmp_path)


def test_runtime_bridge_rejects_missing_python(tmp_path):
    module = _load_module(
        "test_smolvlm2_runtime_bridge",
        "runtime_bridge.py",
    )

    runner = tmp_path / "runtime_runner.py"
    runner.write_text("print('{}')", encoding="utf-8")

    with pytest.raises(module.SmolVLM2RuntimeBridgeError):
        module.run_analysis(
            runtime_python=tmp_path / "missing-python",
            runner_path=runner,
            job_type="vision_analysis",
            input_path=tmp_path / "image.jpg",
            execution={"mode": "cpu"},
        )


def test_runtime_status_missing_python_is_not_ready(tmp_path):
    module = _load_module(
        "test_smolvlm2_runtime_status",
        "runtime_status.py",
    )

    status = module.runtime_status(
        tmp_path / "missing-python",
        "cpu",
    )

    assert status["ready"] is False
    assert status["selected_backend"] == "cpu"
    assert status["missing_modules"]


def test_installation_plan_rejects_missing_python(tmp_path):
    module = _load_module(
        "test_smolvlm2_runtime_installation",
        "runtime_installation.py",
    )

    with pytest.raises(module.SmolVLM2InstallationError):
        module.installation_plan(
            tmp_path / "missing-python",
            "cpu",
        )


def test_runtime_runner_rejects_unknown_job_type(monkeypatch):
    module = _load_module(
        "test_smolvlm2_runtime_runner",
        "runtime_runner.py",
    )

    request = {
        "job_type": "unknown_job",
        "input_path": "dummy.jpg",
        "execution": {"mode": "cpu"},
        "options": {},
    }

    class FakeStdin:
        def read(self):
            return json.dumps(request)

    class FakeStdout:
        def __init__(self):
            self.value = ""

        def write(self, value):
            self.value += value

    fake_stdout = FakeStdout()

    monkeypatch.setattr(module.sys, "stdin", FakeStdin())
    monkeypatch.setattr(module.sys, "stdout", fake_stdout)

    class DummyEngine:
        pass

    monkeypatch.setattr(
        module,
        "load_engine",
        lambda: DummyEngine(),
    )

    result = module.main()

    assert result == 1

    response = json.loads(fake_stdout.value)

    assert response["ok"] is False
    assert response["error"]["type"] == "RuntimeError"
    assert "Nicht unterstuetzter Runtime-Jobtyp" in response["error"]["message"]
