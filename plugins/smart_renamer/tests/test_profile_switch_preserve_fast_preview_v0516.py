from pathlib import Path
from services.rule_stack_merge import merge_profile_rules

ROOT=Path(__file__).resolve().parents[1]

def pr(label):
    return {"type":"schema","label":label,"source":"Profil","enabled":True}

def ur(value="-sd"):
    return {"type":"remove_before_extension","value":value,"source":"Benutzer","enabled":True}

def test_standard_to_plex_keeps_user_rule():
    rules=[pr("Standard"),ur()]
    rules=merge_profile_rules(rules,[pr("Plex")])
    assert any(r.get("source")=="Benutzer" and r.get("value")=="-sd" for r in rules)
    assert any(r.get("source")=="Profil" and r.get("label")=="Plex" for r in rules)
    assert not any(r.get("label")=="Standard" for r in rules)

def test_multiple_profile_changes_do_not_delete_custom_rules():
    rules=[pr("Standard"),ur("-sd"),{"type":"trim","source":"KI"},{"type":"trim","source":"Plugin"},{"type":"trim","source":"ReNamer"}]
    for name in ("Plex","Jellyfin","Emby","Kodi"):
        rules=merge_profile_rules(rules,[pr(name)])
    assert [r.get("source") for r in rules].count("Benutzer")==1
    assert [r.get("source") for r in rules].count("KI")==1
    assert [r.get("source") for r in rules].count("Plugin")==1
    assert [r.get("source") for r in rules].count("ReNamer")==1
    profiles=[r for r in rules if r.get("source")=="Profil"]
    assert len(profiles)==1 and profiles[0]["label"]=="Kodi"

def test_desktop_apply_profile_uses_merge():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    block=text[text.index("def _apply_profile"):text.index("def _render_rules")]
    assert "merge_profile_rules" in block
    assert "self.rules = [dict(rule) for rule in profile.get" not in block

def test_live_preview_is_faster():
    plugin=(ROOT/"plugin.py").read_text(encoding="utf-8")
    web=(ROOT/"index.html").read_text(encoding="utf-8")
    assert "self.preview_timer.setInterval(35)" in plugin
    assert "timer=setTimeout(preview,35)" in web
