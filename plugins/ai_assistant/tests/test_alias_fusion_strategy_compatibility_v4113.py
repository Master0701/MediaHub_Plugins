from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_character_alias_identity_fusion_v418.py"
)


def test_old_exact_strategy_assertion_is_removed():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert (
        '== "character_alias_identity_fusion_v418"'
        not in text
    )
    assert (
        'startswith(\n'
        '        "character_alias_identity_fusion_v"\n'
        '    )'
        in text
    )
