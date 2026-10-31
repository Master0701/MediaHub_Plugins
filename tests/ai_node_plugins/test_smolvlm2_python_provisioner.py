from __future__ import annotations

import importlib.util
from pathlib import Path

PLUGIN_DIR = (
    Path(__file__).resolve().parents[2]
    / "ai_node_plugins"
    / "smolvlm2"
)


def test_python_provisioner_requires_venv_capable_distribution():
    path = PLUGIN_DIR / "python_provisioner.py"
    spec = importlib.util.spec_from_file_location(
        "smolvlm2_python_provisioner_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert "embed" not in module.PYTHON_FILENAME.lower(), (
        "Die Embeddable-Python-Version besitzt kein venv-Modul "
        "und ist fuer die isolierte SmolVLM2-Runtime ungeeignet."
    )
