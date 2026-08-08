from pathlib import Path

from services.media_detection import MediaDetector
from services.media_scanner import MediaScanner


def test_release_suffix_after_episode_number_is_still_series(tmp_path: Path):
    path = tmp_path / "rsg-12-monkeys-s01e01rr-sd.mkv"
    path.write_text("x", encoding="utf-8")

    result = MediaDetector().detect(path)

    assert result.media_type == "series"
    assert result.season == "01"
    assert result.episode == "01"


def test_real_12_monkeys_s01e01rr_case_is_not_movie(tmp_path: Path):
    episode_dir = tmp_path / "Staffel 1" / "12 Monkeys S01E01 Gesplittert-RSG"
    subs = episode_dir / "Subs"
    subs.mkdir(parents=True)

    video = episode_dir / "rsg-12-monkeys-s01e01rr-sd.mkv"
    video.write_text("x", encoding="utf-8")
    (subs / "rsg-12-monkeys-s01e01rr-sd-forced.idx").write_text("x", encoding="utf-8")
    (subs / "rsg-12-monkeys-s01e01rr-sd-forced.sub").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path)}])

    assert len(items) == 1
    assert items[0].media_type == "series"
    assert items[0].season == "01"
    assert items[0].episode == "01"
    assert len(items[0].companion_files) == 2
