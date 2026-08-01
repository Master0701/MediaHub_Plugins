import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "tests" / "test_event_initialization_order_v415.py"


def test_v415_regression_test_is_valid_python():
    text = TEST_PATH.read_text(encoding="utf-8")
    ast.parse(text)


def test_v415_regression_test_has_stable_version_check():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert "_version_tuple(text) >= (4, 1, 0)" in text
    assert 'VERSION = "4.1.7"' not in text
