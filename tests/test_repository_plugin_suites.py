from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "plugin_test_runner.py"


def _load_runner():
    module_name = "mediahub_plugin_test_runner"
    spec = importlib.util.spec_from_file_location(
        module_name,
        RUNNER_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)

    # Python 3.14 benötigt das Modul bereits während exec_module()
    # in sys.modules, damit dataclasses die Modul-Namespaces der
    # String-Annotationen korrekt auflösen kann.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def test_all_plugin_suites_in_isolated_processes() -> None:
    runner = _load_runner()
    results = runner.run_all_plugin_suites(print_output=True)
    failures = [result for result in results if not result.success]

    if failures:
        pytest.fail(
            runner.format_failures(results),
            pytrace=False,
        )
