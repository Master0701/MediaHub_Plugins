from services.rule_engine import RenameRuleEngine

def apply(name, rules):
    return RenameRuleEngine().apply(name, rules)["proposed_name"]

def test_remove_start_count():
    assert apply("rsg-12-monkeys.mkv", [{"type":"remove_start","count":4,"enabled":True}]) == "12-monkeys.mkv"

def test_remove_start_exact_trace_shape():
    rule={"type":"remove_start","source":"Benutzer","enabled":True,"length":4,"count":0}
    assert apply("rsg-12-monkeys.mkv", [rule]) == "12-monkeys.mkv"

def test_remove_end_count():
    assert apply("12-monkeysXYZ.mkv", [{"type":"remove_end","count":3,"enabled":True}]) == "12-monkeys.mkv"

def test_remove_end_length_fallback():
    assert apply("12-monkeysXYZ.mkv", [{"type":"remove_end","count":0,"length":3,"enabled":True}]) == "12-monkeys.mkv"
