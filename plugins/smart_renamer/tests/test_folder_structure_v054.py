from pathlib import Path

from services.media_scanner import MediaScanner


def test_series_folder_detects_collection_and_seasons(tmp_path: Path):
    root = tmp_path / "Breaking Bad"
    s1 = root / "Staffel 01"
    s2 = root / "Season 2"
    s1.mkdir(parents=True)
    s2.mkdir(parents=True)
    (s1 / "S01E01.mkv").write_text("x", encoding="utf-8")
    (s2 / "S02E01.mkv").write_text("x", encoding="utf-8")

    items, skipped = MediaScanner().scan([{"path": str(root)}])

    assert skipped == []
    assert len(items) == 2
    context = items[0].detection_data["folder_context"]
    assert context["collection_type"] == "series"
    assert context["collection_title"] == "Breaking Bad"
    assert set(context["season_map"]) == {"01", "02"}


def test_season_folder_fills_missing_season(tmp_path: Path):
    root = tmp_path / "Serie"
    season = root / "Staffel 03"
    season.mkdir(parents=True)
    path = season / "Folge 7.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert items[0].season == "03"
    assert items[0].episode == "07"


def test_extra_folder_marks_item_as_extra(tmp_path: Path):
    root = tmp_path / "Film"
    extras = root / "Extras"
    extras.mkdir(parents=True)
    path = extras / "Interview.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    item = items[0]
    assert item.is_extra is True
    relation = item.detection_data["folder_relation"]
    assert relation["is_extra_folder"] is True
    assert relation["folder_role"] == "extra"


def test_cd_folder_fills_part(tmp_path: Path):
    root = tmp_path / "Hoerbuch"
    cd2 = root / "CD2"
    cd2.mkdir(parents=True)
    path = cd2 / "Kapitel 1.mp3"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert items[0].part == "2"
    assert items[0].detection_data["folder_relation"]["folder_role"] == "part"


def test_mixed_folder_is_marked_mixed(tmp_path: Path):
    root = tmp_path / "Sammlung"
    root.mkdir()
    (root / "Film 2024.mkv").write_text("x", encoding="utf-8")
    (root / "01 - Lied.flac").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    context = items[0].detection_data["folder_context"]
    assert context["collection_type"] == "mixed"


def test_collection_context_does_not_override_explicit_metadata(tmp_path: Path):
    root = tmp_path / "Serie"
    season = root / "Staffel 03"
    season.mkdir(parents=True)
    path = season / "Folge 7.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([
        {
            "path": str(root),
            "metadata": {
                "staffel": "09",
                "titel": "Manuell",
                "media_type": "series",
            },
        }
    ])

    assert items[0].season == "09"
    assert items[0].title == "Manuell"


def test_recursive_false_keeps_folder_context_local(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "S01E01.mkv").write_text("x", encoding="utf-8")
    nested = root / "Staffel 02"
    nested.mkdir()
    (nested / "S02E01.mkv").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([
        {"path": str(root), "recursive": False}
    ])

    assert len(items) == 1
    assert items[0].season == "01"


def test_folder_context_is_serializable(tmp_path: Path):
    root = tmp_path / "Filmreihe"
    root.mkdir()
    (root / "Film 2024.mkv").write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    payload = items[0].to_dict()
    assert "folder_context" in payload["detection_data"]
    assert payload["detection_data"]["folder_context"]["root_path"] == str(root)
