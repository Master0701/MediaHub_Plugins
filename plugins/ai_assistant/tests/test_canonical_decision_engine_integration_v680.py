from pathlib import Path


def test_canonical_decision_engine_integrated_v680():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.canonical_decision_engine "
        "import CanonicalDecisionEngine"
        in text
    )
    assert (
        "self.canonical_decision_engine = "
        "CanonicalDecisionEngine()"
        in text
    )
    assert (
        "canonical_decisions = "
        "self.canonical_decision_engine.build("
        in text
    )
    assert '"canonical_decisions": canonical_decisions' in text
    assert (
        'context.document["canonical_decisions"] = '
        "canonical_decisions"
        in text
    )
