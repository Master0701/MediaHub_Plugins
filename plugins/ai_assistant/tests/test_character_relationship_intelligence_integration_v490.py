from pathlib import Path


def test_plugin_integrates_character_relationship_intelligence():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")
    assert "CharacterRelationshipIntelligence" in text
    assert '"character_relationship_intelligence"' in text
    assert "character_relationship_intelligence.analyze" in text
