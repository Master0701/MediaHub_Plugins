from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_desktop_all_advanced_fields_are_wired():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    for field in ('self.position','self.length','self.count_chars','self.needle','self.regex_pattern','self.regex_replacement','self.case_sensitive','self.replace_all','self.whole_word','self.include_match'):
        assert field in text
    assert 'self.preview_timer.setInterval(35)' in text
    assert 'Live-Vorschau wird aktualisiert' in text
    assert '_live_preview_toggled' in text

def test_form_changed_updates_rule_then_schedules_preview():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    start=text.index('def _form_changed')
    end=text.index('def _schedule_preview',start)
    block=text[start:end]
    assert 'rule.update' in block
    assert 'self._schedule_preview()' in block

def test_web_all_new_fields_are_live_wired():
    text=(ROOT/'index.html').read_text(encoding='utf-8')
    assert "'position','length','countChars','needle','regexPattern','regexReplacement'" in text
    assert "'caseSensitive','replaceAll','wholeWord','includeMatch'" in text
    assert "timer=setTimeout(preview,35)" in text
    assert "liveEditorFields" in text
