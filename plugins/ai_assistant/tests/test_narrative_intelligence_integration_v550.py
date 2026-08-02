from pathlib import Path


def test_plugin_integrates_narrative_intelligence_v550():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.narrative_intelligence "
        "import NarrativeIntelligence"
        in text
    )
    assert (
        "self.narrative_intelligence = NarrativeIntelligence()"
        in text
    )
    assert (
        "narrative_intelligence = "
        "self.narrative_intelligence.analyze("
        in text
    )
    assert '"narrative_intelligence": narrative_intelligence' in text
    assert (
        'context.document["narrative_intelligence"] = '
        "narrative_intelligence"
        in text
    )
