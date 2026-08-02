from pathlib import Path


def test_plugin_integrates_entity_intelligence_v500():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert "from services.entity_intelligence import EntityIntelligence" in text
    assert "self.entity_intelligence = EntityIntelligence()" in text
    assert "entity_intelligence = self.entity_intelligence.analyze" in text
    assert '"entity_intelligence": entity_intelligence' in text
    assert 'list(entity_intelligence.get("nodes") or [])' in text
    assert 'list(entity_intelligence.get("edges") or [])' in text
