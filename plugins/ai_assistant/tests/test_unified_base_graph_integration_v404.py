import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _plugin_text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def test_plugin_passes_base_graph_to_builder():
    text = _plugin_text()

    assert "knowledge_result=knowledge," in text
    assert "parser_result=parsed," in text
    assert "semantic_result=semantic," in text
    assert "classified_fields=classified_fields" in text
    assert "scan_result=scan," in text


def test_plugin_still_passes_event_and_relationship_groups():
    text = _plugin_text()

    assert 'relationship_intelligence.get("nodes")' in text
    assert 'event_intelligence.get("nodes")' in text
    assert 'relationship_intelligence.get("edges")' in text
    assert 'event_intelligence.get("edges")' in text


def test_plugin_syntax_is_valid():
    ast.parse(_plugin_text())


def test_version_is_404():
    text = _plugin_text()
    import re

    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    assert tuple(int(item) for item in match.groups()) >= (4, 0, 0)
