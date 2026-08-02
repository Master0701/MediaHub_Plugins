from pathlib import Path


def test_plugin_integrates_narrative_extractor_v560():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.narrative_extractor "
        "import NarrativeExtractor"
        in text
    )
    assert "self.narrative_extractor = NarrativeExtractor()" in text
    assert (
        "narrative_extraction = "
        "self.narrative_extractor.extract("
        in text
    )
    assert '"narrative_extraction": narrative_extraction' in text
    assert (
        'context.document["narrative_extraction"] = '
        "narrative_extraction"
        in text
    )
