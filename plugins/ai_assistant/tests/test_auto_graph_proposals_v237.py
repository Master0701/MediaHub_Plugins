from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_auto_proposal_generation_api_exists():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def generate_knowledge_graph_proposals(self):" in text
    assert "self.knowledge_engine.propose_relationships(" in text
    assert "self.graph_proposals.add_many(" in text


def test_manual_entity_can_store_franchise_and_universe():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "self.graph_entity_franchise" in text
    assert "self.graph_entity_universe" in text
    assert 'metadata["franchise"] = franchise' in text
    assert 'metadata["universe"] = universe' in text


def test_auto_proposal_button_exists():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'QPushButton("Automatisch vorschlagen")' in text
    assert "self.generate_graph_proposals" in text
