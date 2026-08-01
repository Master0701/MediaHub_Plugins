from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES = (
    ROOT / "tests" / "test_complete_graph_validation_groups_v433.py",
    ROOT / "tests" / "test_graph_validation_initialization_order_v431.py",
    ROOT / "tests" / "test_franchise_relation_integration_v440.py",
)


def test_no_obsolete_fixed_version_assertions_remain():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in FILES
    )

    assert 'VERSION = "4.3.' not in combined
    assert 'VERSION = "4.4.1"' not in combined


def test_franchise_relations_are_expected_by_graph_group_test():
    text = FILES[0].read_text(encoding="utf-8")

    assert '"franchise_relations"' in text
