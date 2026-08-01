import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def test_current_plugin_version_and_syntax():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    ast.parse(text)
    import re

    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    assert tuple(int(item) for item in match.groups()) >= (4, 0, 0)
def test_dataflow_arguments_remain_current():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    assert "knowledge_result=knowledge," in text
    assert "parser_result=parsed," in text
    assert "semantic_result=semantic," in text
    assert "scan_result=scan," in text

