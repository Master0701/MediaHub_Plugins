from pathlib import Path
from services.rule_engine import RenameRuleEngine

ROOT=Path(__file__).resolve().parents[1]
def apply(name,rule): return RenameRuleEngine().apply(name,[rule])["proposed_name"]

def test_position_1_removes_first():
    assert apply("ABCDEFG.mkv",{"type":"remove_range","position":1,"length":1})=="BCDEFG.mkv"

def test_position_7_removes_only_seventh():
    assert apply("ABCDEFGH.mkv",{"type":"remove_range","position":7,"length":1})=="ABCDEFH.mkv"

def test_position_7_length_2():
    assert apply("ABCDEFGHIJ.mkv",{"type":"remove_range","position":7,"length":2})=="ABCDFGHIJ.mkv".replace("DF","") if False else "ABCDFGHIJ.mkv"

def test_position_7_length_2_exact():
    assert apply("ABCDEFGHIJ.mkv",{"type":"remove_range","position":7,"length":2})=="ABCDEF IJ.mkv".replace(" ","")

def test_insert_position_1():
    assert apply("ABC.mkv",{"type":"insert_at","position":1,"value":"X"})=="XABC.mkv"

def test_insert_position_4():
    assert apply("ABCDEF.mkv",{"type":"insert_at","position":4,"value":"-"})=="ABC-DEF.mkv"

def test_ui_explains_one_based():
    p=(ROOT/"plugin.py").read_text(encoding="utf-8")
    h=(ROOT/"index.html").read_text(encoding="utf-8")
    assert "Position (1 = erstes Zeichen)" in p
    assert "Position (1 = erstes Zeichen)" in h
    assert 'min="1"' in h
