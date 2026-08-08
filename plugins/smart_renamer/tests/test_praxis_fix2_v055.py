from pathlib import Path

from services.media_detection import MediaDetector
from services.media_scanner import MediaScanner


def test_s011_release_typo_normalizes_to_season_11(tmp_path: Path):
    path = tmp_path / "utopia-csilv-s011e02-xvid.avi"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "series"
    assert result.season == "11"
    assert result.episode == "02"


def test_sample_video_is_grouped_not_counted_as_episode(tmp_path: Path):
    episode = tmp_path / "S11" / "CSI.Las.Vegas.S11E02"
    sample_dir = episode / "Sample"
    sample_dir.mkdir(parents=True)

    main = episode / "utopia-csilv-s011e02-xvid.avi"
    sample = sample_dir / "utopia-csilv-s011e02-xvid-sample.avi"
    main.write_text("main", encoding="utf-8")
    sample.write_text("sample", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path)}])

    assert len(items) == 1
    assert items[0].path == main
    assert items[0].season == "11"
    assert any(c["role"] == "sample" for c in items[0].companion_files)


def test_thumbs_db_is_grouped_not_unknown(tmp_path: Path):
    episode = tmp_path / "S07" / "CSI.Las.Vegas.S07E03"
    episode.mkdir(parents=True)

    video = episode / "isd-csidxvid-s07e03.avi"
    thumbs = episode / "thumbs.db"
    video.write_text("video", encoding="utf-8")
    thumbs.write_text("cache", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path)}])

    assert len(items) == 1
    assert items[0].path == video
    assert any(c["role"] == "system" for c in items[0].companion_files)


def test_url_file_is_grouped_not_unknown(tmp_path: Path):
    episode = tmp_path / "S10" / "CSI.Las.Vegas.S10E13"
    episode.mkdir(parents=True)

    video = episode / "utopia-csilv-s10e13-xvid.avi"
    link = episode / "funxd.in.url"
    video.write_text("video", encoding="utf-8")
    link.write_text("[InternetShortcut]", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path)}])

    assert len(items) == 1
    assert any(c["role"] == "link" for c in items[0].companion_files)
