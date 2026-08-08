from pathlib import Path

from services.media_detection import MediaDetector
from services.media_scanner import MediaScanner
from services.rule_engine import RenameRuleEngine


def test_detects_series_sxxexx_and_episode_title(tmp_path: Path):
    path = tmp_path / "Star Trek Strange New Worlds S02E03 Tomorrow.mkv"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "series"
    assert result.season == "02"
    assert result.episode == "03"
    assert result.title == "Star Trek Strange New Worlds"
    assert result.episode_title == "Tomorrow"
    assert result.confidence >= 0.9


def test_detects_series_1x02(tmp_path: Path):
    path = tmp_path / "Serie 1x02 Folge Zwei.mp4"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "series"
    assert result.season == "01"
    assert result.episode == "02"


def test_detects_movie_year_and_edition(tmp_path: Path):
    path = tmp_path / "Blade Runner 1982 Directors Cut 1080p.mkv"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "movie"
    assert result.year == "1982"
    assert result.edition == "Director's Cut"
    assert "Blade Runner" in result.title


def test_detects_audiobook_by_extension(tmp_path: Path):
    path = tmp_path / "Der Hobbit.m4b"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "audiobook"
    assert result.title == "Der Hobbit"


def test_detects_numbered_music_track(tmp_path: Path):
    path = tmp_path / "01 - Songtitel.flac"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "music"
    assert result.title == "Songtitel"
    assert result.extra["track"] == "01"


def test_explicit_metadata_overrides_detection(tmp_path: Path):
    path = tmp_path / "Film 2024.mkv"
    path.write_text("x", encoding="utf-8")

    scanned, skipped = MediaScanner().scan([
        {
            "path": str(path),
            "metadata": {
                "media_type": "series",
                "titel": "Manueller Titel",
                "staffel": "09",
                "episode": "11",
            },
        }
    ])

    assert skipped == []
    item = scanned[0]
    assert item.media_type == "series"
    assert item.title == "Manueller Titel"
    assert item.season == "09"
    assert item.episode == "11"
    assert item.detection_data["media_type"] == "movie"


def test_mixed_folder_is_marked_in_detection_data(tmp_path: Path):
    (tmp_path / "Film 2024.mkv").write_text("x", encoding="utf-8")
    (tmp_path / "01 - Lied.flac").write_text("x", encoding="utf-8")

    scanned, _ = MediaScanner().scan([{"path": str(tmp_path)}])

    assert {item.media_type for item in scanned} == {"movie", "music"}
    assert all(
        item.detection_data["collection_media_type"] == "mixed"
        for item in scanned
    )


def test_new_schema_placeholders_use_detection_metadata():
    result = RenameRuleEngine().apply(
        "raw.mkv",
        [{
            "type": "schema",
            "template": "[titel] ([jahr]) [edition] [medientyp]",
        }],
        metadata={
            "titel": "Film",
            "jahr": "2024",
            "edition": "Extended Cut",
            "media_type": "movie",
        },
    )

    assert result["proposed_name"] == (
        "Film (2024) Extended Cut movie.mkv"
    )
