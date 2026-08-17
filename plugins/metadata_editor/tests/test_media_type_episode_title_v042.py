from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_media_type_selector_supports_video_movie_series():
    assert 'self.media_type_edit.addItem("Video", "video")' in PLUGIN
    assert 'self.media_type_edit.addItem("Film", "movie")' in PLUGIN
    assert 'self.media_type_edit.addItem("Serie", "series")' in PLUGIN


def test_media_type_is_loaded_and_returned_by_editor():
    assert 'item.get("media_type") or "video"' in PLUGIN
    assert '"media_type": str(' in PLUGIN
    assert 'self.media_type_edit.currentData() or "video"' in PLUGIN


def test_episode_title_is_editable():
    assert "self.episode_title_edit = QLineEdit()" in PLUGIN
    assert (
        'series_form.addRow("Episodentitel", '
        'self.episode_title_edit)'
    ) in PLUGIN

    assert "episode_title_display" not in PLUGIN


def test_episode_title_is_loaded_and_returned():
    assert 'item.get("episode_title")' in PLUGIN
    assert (
        '"episode_title": '
        'self.episode_title_edit.text().strip()'
    ) in PLUGIN


def test_episode_title_participates_in_change_detection():
    assert "self.episode_title_edit," in PLUGIN


def test_ai_result_can_fill_episode_title():
    assert "self.episode_title_edit.setText(" in PLUGIN
    assert 'fields.get("episode_title")' in PLUGIN


def test_confirmed_metadata_write_remains_required():
    assert '"mode": "confirmed_write"' in PLUGIN
    assert '"automatic_apply_allowed": False' in PLUGIN
    assert '"human_confirmation_required": True' in PLUGIN
