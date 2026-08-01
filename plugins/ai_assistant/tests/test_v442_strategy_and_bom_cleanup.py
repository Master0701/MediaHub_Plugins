from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"
STRATEGY_TEST_PATH = (
    ROOT
    / "tests"
    / "test_continuity_node_key_normalization_v441.py"
)


def test_plugin_has_no_utf8_bom():
    raw = PLUGIN_PATH.read_bytes()

    assert not raw.startswith(b"\xef\xbb\xbf")


def test_plugin_text_can_be_parsed_without_bom_cleanup():
    text = PLUGIN_PATH.read_text(encoding="utf-8")

    compile(text, str(PLUGIN_PATH), "exec")


def test_old_exact_v441_strategy_assertion_is_removed():
    text = STRATEGY_TEST_PATH.read_text(encoding="utf-8")

    assert (
        '"franchise_relation_intelligence_v441"'
        not in text
    )
    assert (
        'startswith(\n'
        '        "franchise_relation_intelligence_v"\n'
        '    )'
        in text
    )
