import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _version_tuple() -> tuple[int, int, int]:
    text = PLUGIN_PATH.read_text(encoding="utf-8")
    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    return tuple(int(item) for item in match.groups())


def test_plugin_version_is_stable_and_compatible():
    assert _version_tuple() >= (4, 1, 0)


def test_plugin_version_has_three_numeric_parts():
    version = _version_tuple()

    assert len(version) == 3
    assert all(isinstance(item, int) for item in version)


def test_plugin_syntax_is_valid():
    ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
