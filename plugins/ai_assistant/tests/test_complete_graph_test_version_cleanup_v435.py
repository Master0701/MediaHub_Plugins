from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_complete_graph_validation_groups_v433.py"
)


def test_old_exact_v434_assertion_is_removed():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert 'VERSION = "4.3.4"' not in text
    assert 'VERSION = "' in text
