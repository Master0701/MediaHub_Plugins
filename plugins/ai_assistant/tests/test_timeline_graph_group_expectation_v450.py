from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = (
    ROOT
    / "tests"
    / "test_complete_graph_validation_groups_v433.py"
)


def test_timeline_order_group_is_expected():
    text = TARGET.read_text(encoding="utf-8")

    assert '"timeline_order_intelligence"' in text
