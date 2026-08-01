import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_graph_validation_initialization_order_v431.py"
)


def test_v431_test_file_is_valid_python():
    text = TEST_PATH.read_text(encoding="utf-8")
    ast.parse(text)


def test_old_rigid_assignment_search_is_removed():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert '"character_graph ="' not in text
    assert "ast.walk" in text
