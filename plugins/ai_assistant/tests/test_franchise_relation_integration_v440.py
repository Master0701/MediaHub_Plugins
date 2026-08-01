import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def test_plugin_syntax_and_version():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    ast.parse(text)
    assert 'VERSION = "' in text


def test_franchise_relations_are_fully_integrated():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    assert "FranchiseRelationIntelligence.analyze(" in text
    assert "franchise_relations," in text
    assert (
        'context.document["franchise_relations"]'
        in text
    )
    assert (
        '"franchise_relations": franchise_relations'
        in text
    )
