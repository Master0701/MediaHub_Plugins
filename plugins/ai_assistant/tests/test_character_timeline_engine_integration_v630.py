from pathlib import Path


def test_character_timeline_engine_integrated_v630():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.character_timeline_engine "
        "import CharacterTimelineEngine"
        in text
    )
    assert (
        "self.character_timeline_engine = CharacterTimelineEngine()"
        in text
    )
    assert (
        "character_timeline = "
        "self.character_timeline_engine.build("
        in text
    )
    assert '"character_timeline": character_timeline' in text
    assert (
        'context.document["character_timeline"] = '
        "character_timeline"
        in text
    )
