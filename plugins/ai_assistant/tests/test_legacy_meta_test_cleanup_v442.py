from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGETS = (
    ROOT / "tests" / "test_complete_graph_test_version_cleanup_v435.py",
    ROOT / "tests" / "test_graph_validation_version_regression_v435.py",
)


def test_legacy_meta_tests_no_longer_require_43_prefix():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in TARGETS
    )

    assert 'assert \'VERSION = "4.3.\' in text' not in combined
    assert 'assert \'VERSION = "\' in text' in combined
