"""Existing healthy venvs must work without managed base Python."""
import importlib.util
from pathlib import Path


def test_create_runtime_reuses_ready_venv(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[2] / "ai_node_plugins" / "smolvlm2" / "runtime.py"
    spec = importlib.util.spec_from_file_location("runtime_reuse_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / "smolvlm2"
    python = root / "venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(module, "runtime_root", lambda: root)
    monkeypatch.setattr(module, "models_root", lambda: tmp_path / "models")
    monkeypatch.setattr(module, "_venv_python_path", lambda: python)
    monkeypatch.setattr(module, "inspect_runtime", lambda: {"ready": True, "python": str(python)})
    def reject():
        raise AssertionError("Must not request base Python for healthy venv")
    monkeypatch.setattr(module, "runtime_base_python", reject)
    assert module.create_runtime()["ready"] is True
    assert not (root / "state.json").exists()
