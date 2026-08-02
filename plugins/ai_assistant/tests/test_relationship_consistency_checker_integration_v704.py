from pathlib import Path


def test_relationship_consistency_checker_integrated_v704():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.relationship_consistency_checker "
        "import RelationshipConsistencyChecker"
        in text
    )
    assert (
        "self.relationship_consistency_checker = "
        "RelationshipConsistencyChecker()"
        in text
    )
    assert (
        "relationship_consistency = "
        "self.relationship_consistency_checker.build("
        in text
    )
    assert (
        '"relationship_consistency": relationship_consistency'
        in text
    )
    assert (
        'context.document["relationship_consistency"] = '
        "relationship_consistency"
        in text
    )
