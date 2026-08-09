from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_desktop_modular():
    t=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "QStackedWidget" in t and "self.rule_stack" in t and "_rule_page_key" in t and "Regelstapel" in t
def test_schema_module():
    t=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert 'schema_form=add_page("schema"' in t and "Beschriftungs-Reihenfolge" in t
def test_web_modular():
    t=(ROOT/"index.html").read_text(encoding="utf-8")
    assert "rulePageFor" in t and "showRulePage" in t and 'data-page="schema"' in t and 'data-page="position"' in t
def test_advanced_stays():
    t=(ROOT/"plugin.py").read_text(encoding="utf-8")
    for x in ("Erweitert suchen/ersetzen","RegEx ersetzen","Zeichenbereich entfernen","Vor/Nach Fundstelle entfernen"): assert x in t
