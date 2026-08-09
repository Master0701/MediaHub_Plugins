from pathlib import Path
from services.rule_engine import RenameRuleEngine
ROOT=Path(__file__).resolve().parents[1]
def apply(name,rule): return RenameRuleEngine().apply(name,[rule])["proposed_name"]

def test_remove_ws_whole_word():
    assert apply("Serie.WS.German.mkv",{"type":"replace_advanced","old":"WS","new":"","whole_word":True,"replace_all":True})=="Serie..German.mkv"
def test_remove_range():
    assert apply("ABCDEFGHIJ.mkv",{"type":"remove_range","position":3,"length":4})=="ABGHIJ.mkv"
def test_remove_start_end():
    assert apply("ABCDEF.mkv",{"type":"remove_start","count":2})=="CDEF.mkv"
    assert apply("ABCDEF.mkv",{"type":"remove_end","count":2})=="ABCD.mkv"
def test_insert_at():
    assert apply("ABCDEF.mkv",{"type":"insert_at","position":4,"value":"-X-"})=="ABC-X-DEF.mkv"
def test_regex():
    assert apply("Serie.S01E03.WS.mkv",{"type":"regex_replace","pattern":r"\.WS$","replacement":"","replace_all":True})=="Serie.S01E03.mkv"
def test_relative():
    assert apply("PREFIX-Serie.mkv",{"type":"remove_relative","needle":"-","relative_mode":"before","include_match":True})=="Serie.mkv"
    assert apply("Serie-TRASH.mkv",{"type":"remove_relative","needle":"-","relative_mode":"after","include_match":True})=="Serie.mkv"
def test_normalize():
    assert apply("CSI.Las_Vegas.S01E01.mkv",{"type":"normalize_separators","separators":"._"})=="CSI Las Vegas S01E01.mkv"
def test_extension_protected():
    assert apply("movie.mkv",{"type":"replace_advanced","old":"mkv","new":"avi"})=="movie.mkv"
def test_ui_markers():
    p=(ROOT/"plugin.py").read_text(encoding="utf-8"); h=(ROOT/"index.html").read_text(encoding="utf-8")
    assert "Erweitert suchen/ersetzen" in p and "RegEx ersetzen" in p and "Zeichenbereich entfernen" in p
    assert 'value="replace_advanced"' in h and 'id="position"' in h and 'id="wholeWord"' in h
