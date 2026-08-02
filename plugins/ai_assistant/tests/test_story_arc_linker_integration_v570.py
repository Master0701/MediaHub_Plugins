from pathlib import Path


def test_story_arc_linker_integrated_v570():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")
    assert "from services.story_arc_linker import StoryArcLinker" in text
    assert "self.story_arc_linker = StoryArcLinker()" in text
    assert "story_arc_linking = self.story_arc_linker.link(" in text
    assert '"story_arc_linking": story_arc_linking' in text
