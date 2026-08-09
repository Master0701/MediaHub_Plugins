from pathlib import Path
from services.rule_stack_merge import merge_profile_rules

ROOT=Path(__file__).resolve().parents[1]

def profile_rule(label="Plex"):
    return {"type":"schema","label":label,"source":"Profil","enabled":True}

def test_profile_rules_run_before_custom_rules():
    existing=[
        {"type":"remove_range","position":1,"length":1,"source":"Benutzer","enabled":True},
        {"type":"trim","source":"KI","enabled":True},
    ]
    merged=merge_profile_rules(existing,[profile_rule("Plex")])
    assert [r["source"] for r in merged]==["Profil","Benutzer","KI"]

def test_multiple_user_rules_survive_profile_change():
    existing=[
        {"type":"remove_before_extension","value":"-sd","source":"Benutzer","enabled":True},
        {"type":"replace_advanced","old":"rr","new":"","source":"Benutzer","enabled":True},
    ]
    merged=merge_profile_rules(existing,[profile_rule("Plex")])
    users=[r for r in merged if r.get("source")=="Benutzer"]
    assert len(users)==2
    assert users[0]["value"]=="-sd"
    assert users[1]["old"]=="rr"

def test_desktop_has_explicit_apply_workflow():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "Regel übernehmen" in text
    assert "Neue Regel" in text
    assert "def _apply_current_rule" in text
    assert "self._form_changed()" in text

def test_web_has_explicit_apply_workflow():
    text=(ROOT/"index.html").read_text(encoding="utf-8")
    assert 'id="applyRule"' in text
    assert 'id="newRule"' in text
    assert "$('applyRule').onclick" in text
    assert "$('newRule').onclick" in text

def test_fast_preview_stays_enabled():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "self.preview_timer.setInterval(35)" in text
