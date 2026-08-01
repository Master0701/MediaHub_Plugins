import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def test_current_base_graph_arguments():
    text = _text()

    assert "knowledge_result=knowledge," in text
    assert "parser_result=parsed," in text
    assert "semantic_result=semantic," in text
    assert "classified_fields=classified_fields," in text
    assert "scan_result=scan," in text


def test_undefined_old_argument_names_are_absent():
    text = _text()

    assert "knowledge_result=knowledge_result," not in text
    assert "parser_result=parser_result," not in text
    assert "semantic_result=semantic_result," not in text
    assert "scan_result=scan_result," not in text


def test_universe_and_event_groups_are_included():
    text = _text()

    assert 'relationship_intelligence.get("nodes")' in text
    assert 'event_intelligence.get("nodes")' in text
    assert 'universe_franchise_proposal.get("nodes")' in text

    assert 'relationship_intelligence.get("edges")' in text
    assert 'event_intelligence.get("edges")' in text
    assert 'universe_franchise_proposal.get("edges")' in text


def test_plugin_syntax_and_version():
    text = _text()

    ast.parse(text)
    import re

    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    assert tuple(int(item) for item in match.groups()) >= (4, 0, 0)
