from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_graph_validation_initialization_order_v431.py"
)


def test_old_exact_v432_assertion_is_removed():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert 'VERSION = "4.3.2"' not in text
    assert 'VERSION = "4.3.' in text
