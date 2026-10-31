from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_DIR = (
    Path(__file__).resolve().parents[2]
    / "ai_node_plugins"
    / "smolvlm2"
)


def test_windows_does_not_fallback_to_other_python(monkeypatch):
    path = PLUGIN_DIR / "python_runtime.py"

    spec = importlib.util.spec_from_file_location(
        "smolvlm2_python_runtime_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module.os, "name", "nt")

    monkeypatch.setattr(
        module,
        "private_python",
        lambda: None,
    )

    monkeypatch.setattr(
        module,
        "configured_python",
        lambda: Path("C:/OtherPython/python.exe"),
    )

    monkeypatch.setattr(
        module,
        "launcher_candidates",
        lambda: [Path("C:/Launcher/python.exe")],
    )

    monkeypatch.setattr(
        module,
        "inspect_python",
        lambda executable: {
            "executable": str(executable),
            "available": True,
            "supported": True,
        },
    )

    result = module.discover_python()

    assert result["found"] is False
    assert result["source"] is None



def test_windows_rejects_python_without_venv(monkeypatch):
    path = PLUGIN_DIR / "python_runtime.py"

    spec = importlib.util.spec_from_file_location(
        "smolvlm2_python_without_venv_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import subprocess
    import sys

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(
        module,
        "private_python",
        lambda: Path(sys.executable),
    )

    def fake_run(command, **kwargs):
        if "-I" in command:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr="ModuleNotFoundError: No module named 'venv'",
            )

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"major":3,"minor":12,"micro":10,'
                '"bits":"64bit","executable":"python.exe"}'
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.discover_python()

    assert result["found"] is False
