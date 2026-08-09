from services.rule_engine import RenameRuleEngine

def apply(name,rule):
    return RenameRuleEngine().apply(name,[rule])["proposed_name"]

def test_remove_sd_directly_before_extension():
    assert apply("rsg-12-monkeys-s01e01rr-sd.mkv",{"type":"remove_before_extension","value":"-sd"})=="rsg-12-monkeys-s01e01rr.mkv"

def test_remove_three_chars_before_extension_marker():
    assert apply("rsg-12-monkeys-s01e01rr-sd.mkv",{"type":"remove_count_before_marker","needle":".mkv","count":3})=="rsg-12-monkeys-s01e01rr.mkv"

def test_relative_rule_can_see_extension_marker():
    assert apply("abc-sd.mkv",{"type":"remove_relative","needle":".mkv","relative_mode":"after","include_match":False})=="abc-sd.mkv"

def test_only_trailing_sd_removed():
    assert apply("sd-show-s01e01-sd.mkv",{"type":"remove_before_extension","value":"-sd"})=="sd-show-s01e01.mkv"

def test_case_insensitive():
    assert apply("show-SD.mkv",{"type":"remove_before_extension","value":"-sd","case_sensitive":False})=="show.mkv"
