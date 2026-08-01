import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def test_runtime_variable_names_are_valid():
    text = _text()

    assert "knowledge_result=knowledge," in text
    assert "parser_result=parsed," in text
    assert "semantic_result=semantic," in text
    assert "scan_result=scan," in text

    assert "knowledge_result=knowledge_result," not in text
    assert "parser_result=parser_result," not in text
    assert "semantic_result=semantic_result," not in text
    assert "scan_result=scan_result," not in text


def test_universe_data_is_included_in_final_graph():
    text = _text()

    assert 'universe_franchise_proposal.get("nodes")' in text
    assert 'universe_franchise_proposal.get("edges")' in text


def test_graph_is_built_after_universe_merge():
    text = _text()

    universe_edge_position = text.index(
        'for item in universe_franchise_proposal.get("edges") or []:'
    )
    graph_build_position = text.index(
        "knowledge_graph = self.knowledge_graph_builder.build("
    )

    assert graph_build_position > universe_edge_position


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
