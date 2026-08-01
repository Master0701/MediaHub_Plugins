from pathlib import Path

PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"

def test_manual_entity_gui_exists():
    text = PLUGIN_FILE.read_text(encoding="utf-8")
    assert "Entität hinzufügen" in text
    assert "def create_graph_entity(self):" in text
    assert "create_knowledge_graph_entity" in text

def test_order_editor_accepts_titles_or_ids():
    text = PLUGIN_FILE.read_text(encoding="utf-8")
    assert "Je Zeile eine Entität" in text
    assert "def _resolve_graph_entity_ids(self, lines):" in text
    assert "graph_entity_lookup" in text

def test_relation_and_order_delete_are_confirmed():
    text = PLUGIN_FILE.read_text(encoding="utf-8")
    assert "def delete_graph_relation(self):" in text
    assert "def delete_graph_order(self):" in text
    assert "wirklich dauerhaft löschen" in text
