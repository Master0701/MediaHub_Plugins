import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = (
    ROOT
    / "tests"
    / "test_complete_graph_validation_groups_v433.py"
)


def test_v433_test_file_is_valid_python():
    text = TEST_PATH.read_text(encoding="utf-8")
    ast.parse(text)


def test_service_import_path_is_prepared_first():
    text = TEST_PATH.read_text(encoding="utf-8")

    path_position = text.index(
        "sys.path.insert(0, str(ROOT))"
    )
    import_position = text.index(
        "from services.knowledge_engine."
    )

    assert path_position < import_position
