from pathlib import Path


def test_relationship_confidence_engine_integrated_v620():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.relationship_confidence_engine "
        "import RelationshipConfidenceEngine"
        in text
    )
    assert (
        "self.relationship_confidence_engine = "
        "RelationshipConfidenceEngine()"
        in text
    )
    assert (
        "relationship_confidence = "
        "self.relationship_confidence_engine.build("
        in text
    )
    assert (
        '"relationship_confidence": relationship_confidence'
        in text
    )
    assert (
        'context.document["relationship_confidence"] = '
        "relationship_confidence"
        in text
    )
