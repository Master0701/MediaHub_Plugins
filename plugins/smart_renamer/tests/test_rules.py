from services.rule_engine import RenameRuleEngine

def test_rule_chain_and_extension_protection():
 r=RenameRuleEngine().apply("Aquaman  2023.mkv",[{"type":"replace","old":"Aquaman","new":"Film"},{"type":"trim"},{"type":"prefix","value":"Neu - "}])
 assert r["proposed_name"]=="Neu - Film 2023.mkv"
 assert r["extension_protected"] is True
 assert r["applied_rules"]==["replace","trim","prefix"]

def test_case_remove_and_numbering():
 r=RenameRuleEngine().apply("TEST_sample.mp4",[{"type":"remove","value":"_sample"},{"type":"case","mode":"title"},{"type":"numbering","start":3,"padding":3,"placement":"prefix","separator":" - "}],item_index=1)
 assert r["proposed_name"]=="004 - Test.mp4"

def test_schema_placeholders():
 r=RenameRuleEngine().apply("raw.mkv",[{"type":"schema","template":"[titel] S[staffel]E[episode] ([jahr])"}],metadata={"titel":"Serie","staffel":"02","episode":"03","jahr":"2025"})
 assert r["proposed_name"]=="Serie S02E03 (2025).mkv"

def test_invalid_windows_chars_are_reported():
 r=RenameRuleEngine().apply("Film.mkv",[{"type":"suffix","value":"?"}])
 assert r["warnings"]
