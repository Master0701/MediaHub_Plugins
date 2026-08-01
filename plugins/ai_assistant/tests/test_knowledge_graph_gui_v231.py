from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_graph_gui_contract():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'tabs.addTab(graph_scroll, "Knowledge Graph")' in text
    assert "graph_scroll.setWidget(graph_page)" in text
    assert "def refresh_knowledge_graph(self" in text
    assert "def confirm_graph_relation(self):" in text
    assert "def preview_graph_proposals(self):" in text
    assert "def create_graph_order(self):" in text


def test_graph_gui_does_not_auto_persist_relations():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "propose_knowledge_graph_relationships" in text
    assert "confirm_knowledge_graph_relation" in text
    assert "Diesen Beziehungsvorschlag dauerhaft übernehmen?" in text


def test_graph_snapshot_api_is_exposed():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def get_knowledge_graph_snapshot(self):" in text
    assert '"entities": self.knowledge_engine.all_items()' in text
    assert '"relations": self.knowledge_engine.store.all_relations()' in text
    assert '"orders": self.knowledge_engine.store.all_orders()' in text
