import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"plugin.py").read_text(encoding="utf-8")

def test_plugin_syntax(): ast.parse(TEXT)
def test_import_and_init():
    assert "from services.franchise_connection_intelligence import FranchiseConnectionIntelligence" in TEXT
    assert "self.franchise_connection_intelligence = FranchiseConnectionIntelligence()" in TEXT
def test_scan_graph_context_and_payload():
    assert "franchise_connection_intelligence = (" in TEXT
    assert 'franchise_connection_intelligence.get("nodes")' in TEXT
    assert 'franchise_connection_intelligence.get("edges")' in TEXT
    assert 'context.document["franchise_connection_intelligence"]' in TEXT
    assert '"franchise_connection_intelligence": franchise_connection_intelligence' in TEXT
