import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_plugin_syntax():
    ast.parse(TEXT)


def test_universe_engine_is_integrated():
    assert "from services.universe_intelligence import UniverseIntelligence" in TEXT
    assert "self.universe_intelligence = UniverseIntelligence()" in TEXT
    assert "universe_intelligence = self.universe_intelligence.analyze(" in TEXT
    assert 'universe_intelligence.get("nodes")' in TEXT
    assert 'universe_intelligence.get("edges")' in TEXT
    assert 'context.document["universe_intelligence"]' in TEXT
    assert '"universe_intelligence": universe_intelligence' in TEXT
