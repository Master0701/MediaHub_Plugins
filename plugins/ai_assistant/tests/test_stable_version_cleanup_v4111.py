from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "tests" / "test_stable_plugin_version_v419.py"


def test_stable_version_test_has_no_exact_patch_version():
    text = TEST_PATH.read_text(encoding="utf-8")

    assert "== (4, 1, 9)" not in text
    assert ">= (4, 1, 0)" in text
