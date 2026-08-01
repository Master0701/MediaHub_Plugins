from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_franchise_collection_intelligence_v420.py"
)


def test_old_exact_strategy_assertion_is_removed():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert (
        '== "franchise_collection_intelligence_v420"'
        not in text
    )
    assert (
        'startswith(\n'
        '        "franchise_collection_intelligence_v"\n'
        '    )'
        in text
    )
