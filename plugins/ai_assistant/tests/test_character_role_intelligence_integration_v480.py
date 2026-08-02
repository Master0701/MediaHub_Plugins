from pathlib import Path


def test_plugin_integrates_character_role_intelligence():
    text = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert "CharacterRoleIntelligence" in text
    assert '"character_role_intelligence"' in text
    assert 'character_role_intelligence.get("nodes")' in text
    assert 'character_role_intelligence.get("edges")' in text
