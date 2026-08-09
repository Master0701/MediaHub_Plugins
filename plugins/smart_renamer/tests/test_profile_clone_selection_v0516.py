from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_profile_clone_is_immediately_selected():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    block=text[text.index('if original_source in ("profil","profile")'):text.index('kind=self.rule_type.currentData()', text.index('if original_source in ("profil","profile")'))]
    assert "self._render_rules(row)" in block
    assert "self.rule_list.setCurrentRow(row)" in block
    assert 'self.rule_source.setCurrentText("Benutzer")' in block

def test_profile_clone_is_guarded_against_recursive_form_events():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    block=text[text.index('if original_source in ("profil","profile")'):text.index('kind=self.rule_type.currentData()', text.index('if original_source in ("profil","profile")'))]
    assert "self._updating_form=True" in block
    assert "self._updating_form=False" in block

def test_new_rules_are_user_rules():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    start=text.index("def _add_rule")
    block=text[start:start+500]
    assert '"source":"Benutzer"' in block

def test_final_name_pipeline_remains_present():
    text=(ROOT/"services/rule_engine.py").read_text(encoding="utf-8")
    assert "order_rules_for_final_name" in text

def test_live_preview_stays_35ms():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "self.preview_timer.setInterval(35)" in text
