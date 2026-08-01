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


def test_plugin_has_valid_v4_or_newer_version():
    assert _version_tuple() >= (4, 0, 0)


def test_plugin_syntax_is_valid():
    ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))


def test_current_package_version():
    assert _version_tuple() >= (4, 0, 0)


def test_graph_dataflow_remains_current():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    assert "knowledge_result=knowledge," in text
    assert "parser_result=parsed," in text
    assert "semantic_result=semantic," in text
    assert "scan_result=scan," in text

