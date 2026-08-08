from pathlib import Path

from services.media_scanner import MediaScanner


def test_subtitles_group_under_episode(tmp_path: Path):
    root = tmp_path / "Serie" / "Staffel 1"
    root.mkdir(parents=True)
    video = root / "show-s01e02.mkv"
    sub = root / "show-s01e02-forced.srt"
    video.write_text("video", encoding="utf-8")
    sub.write_text("sub", encoding="utf-8")

    items, skipped = MediaScanner().scan([{"path": str(tmp_path / "Serie")}])

    assert skipped == []
    assert len(items) == 1
    assert items[0].path == video
    assert len(items[0].companion_files) == 1
    assert items[0].companion_files[0]["role"] == "subtitle"
    assert items[0].companion_files[0]["forced"] is True


def test_idx_sub_sfv_from_subs_folder_group_to_episode(tmp_path: Path):
    episode_dir = (
        tmp_path
        / "12 Monkeys"
        / "Staffel 1"
        / "12 Monkeys S01E02 Titel"
    )
    subs = episode_dir / "Subs"
    subs.mkdir(parents=True)

    video = episode_dir / "rsg-12-monkeys-s01e02-sd.mkv"
    video.write_text("video", encoding="utf-8")
    for name in (
        "rsg-12-monkeys-s01e02-sd-forced.idx",
        "rsg-12-monkeys-s01e02-sd-forced.sub",
        "rsg-12-monkeys-s01e02-sd-subs.sfv",
    ):
        (subs / name).write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan(
        [{"path": str(tmp_path / "12 Monkeys")}]
    )

    assert len(items) == 1
    roles = sorted(value["role"] for value in items[0].companion_files)
    assert roles == ["checksum", "subtitle", "subtitle"]


def test_language_is_detected_from_subtitle_filename(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "show-s02e01.mkv").write_text("x", encoding="utf-8")
    (root / "show-s02e01-eng-forced.srt").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    companion = items[0].companion_files[0]
    assert companion["language"] == "en"
    assert companion["forced"] is True


def test_nfo_and_images_group_to_single_video(tmp_path: Path):
    root = tmp_path / "Film"
    root.mkdir()
    video = root / "Film 2024.mkv"
    video.write_text("x", encoding="utf-8")
    (root / "Film 2024.nfo").write_text("x", encoding="utf-8")
    (root / "Film 2024-poster.jpg").write_text("x", encoding="utf-8")
    (root / "Film 2024-fanart.jpg").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert len(items) == 1
    roles = {value["role"] for value in items[0].companion_files}
    assert roles == {"metadata", "poster", "fanart"}


def test_unmatched_companion_remains_visible_for_safety(tmp_path: Path):
    root = tmp_path / "Orphan"
    root.mkdir()
    orphan = root / "nobody.srt"
    orphan.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert len(items) == 1
    assert items[0].path == orphan
    assert items[0].detection_data["companion_unmatched"] is True


def test_grouping_prevents_subtitle_from_inflating_season_count(tmp_path: Path):
    root = tmp_path / "Serie" / "Staffel 1"
    root.mkdir(parents=True)
    for episode in (1, 2):
        (root / f"show-s01e{episode:02d}.mkv").write_text("x", encoding="utf-8")
        (root / f"show-s01e{episode:02d}.srt").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path / "Serie")}])

    assert len(items) == 2
    assert all(item.season == "01" for item in items)
    assert sum(len(item.companion_files) for item in items) == 2


def test_12_monkeys_s01e01rr_style_companions_group_by_episode(tmp_path: Path):
    episode_dir = tmp_path / "Staffel 1" / "12 Monkeys S01E01 Titel"
    subs = episode_dir / "Subs"
    subs.mkdir(parents=True)

    video = episode_dir / "rsg-12-monkeys-s01e01rr-sd.mkv"
    video.write_text("x", encoding="utf-8")
    (subs / "rsg-12-monkeys-s01e01rr-sd-forced.idx").write_text("x", encoding="utf-8")
    (subs / "rsg-12-monkeys-s01e01rr-sd-forced.sub").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(tmp_path / "Staffel 1")}])

    assert len(items) == 1
    assert items[0].path == video
    assert len(items[0].companion_files) == 2


def test_media_item_serializes_companion_files(tmp_path: Path):
    root = tmp_path / "Film"
    root.mkdir()
    (root / "Film 2024.mkv").write_text("x", encoding="utf-8")
    (root / "Film 2024.srt").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])
    payload = items[0].to_dict()

    assert len(payload["companion_files"]) == 1
    assert payload["detection_data"]["companion_count"] == 1
