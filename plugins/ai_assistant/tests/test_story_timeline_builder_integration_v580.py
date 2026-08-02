from pathlib import Path


def test_story_timeline_builder_integrated_v580():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.story_timeline_builder "
        "import StoryTimelineBuilder"
        in text
    )
    assert (
        "self.story_timeline_builder = StoryTimelineBuilder()"
        in text
    )
    assert (
        "story_timeline = self.story_timeline_builder.build("
        in text
    )
    assert '"story_timeline": story_timeline' in text
    assert (
        'context.document["story_timeline"] = story_timeline'
        in text
    )
