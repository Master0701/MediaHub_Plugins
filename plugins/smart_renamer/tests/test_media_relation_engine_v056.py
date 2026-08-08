from pathlib import Path

from models.media_relation import MediaRelation
from services.media_relation_engine import MediaRelationEngine
from services.media_scanner import MediaScanner
from services.naming_profiles import NamingProfileService


def test_multi_episode_filename_is_detected(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    path = root / "Show - S01E05-E06.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    relation = items[0].detection_data["media_relation"]
    assert relation["relation_type"] == "multi_episode"
    assert relation["episode_start"] == "05"
    assert relation["episode_end"] == "06"
    assert relation["review_required"] is True


def test_split_episode_parts_become_merge_candidates(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "Show - S02E03 - cd1.mkv").write_text("1", encoding="utf-8")
    (root / "Show - S02E03 - cd2.mkv").write_text("2", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert len(items) == 2
    relations = [item.detection_data["media_relation"] for item in items]
    assert {r["relation_type"] for r in relations} == {"split_episode"}
    assert {r["part_number"] for r in relations} == {1, 2}
    assert all(r["part_count"] == 2 for r in relations)
    assert all(r["recommended_action"] == "merge_candidate" for r in relations)


def test_split_movie_parts_become_merge_candidates(tmp_path: Path):
    root = tmp_path / "Film"
    root.mkdir()
    (root / "Film (2001) pt1.mkv").write_text("1", encoding="utf-8")
    (root / "Film (2001) pt2.mkv").write_text("2", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    relations = [item.detection_data["media_relation"] for item in items]
    assert {r["relation_type"] for r in relations} == {"split_movie"}
    assert all(r["review_required"] is True for r in relations)


def test_episode_gap_is_only_candidate_not_proven_missing(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "Show - S01E01.mkv").write_text("1", encoding="utf-8")
    (root / "Show - S01E03.mkv").write_text("3", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    for item in items:
        relation = item.detection_data["media_relation"]
        assert relation["missing_episode_candidates"] == ["02"]
        assert relation["relation_type"] == "single"
        assert relation["recommended_action"] == "review"
        assert relation["review_required"] is True


def test_multi_episode_range_covers_gap(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "Show - S01E01.mkv").write_text("1", encoding="utf-8")
    (root / "Show - S01E02-E03.mkv").write_text("2", encoding="utf-8")
    (root / "Show - S01E04.mkv").write_text("4", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])

    assert all(
        not item.detection_data["media_relation"]["missing_episode_candidates"]
        for item in items
    )


def test_relation_model_rejects_unknown_type():
    try:
        MediaRelation(relation_type="not-valid")
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError erwartet")


def test_plex_multi_episode_name():
    service = NamingProfileService()
    value = service.render_relation_name(
        "plex",
        {
            "relation_type": "multi_episode",
            "episode_start": "05",
            "episode_end": "06",
        },
        title="CSI Las Vegas",
        season="1",
    )
    assert value == "CSI Las Vegas - S01E05-E06"


def test_plex_split_episode_name():
    service = NamingProfileService()
    value = service.render_relation_name(
        "plex",
        {
            "relation_type": "split_episode",
            "episode_start": "05",
            "part_number": 2,
        },
        title="CSI Las Vegas",
        season="1",
    )
    assert value == "CSI Las Vegas - S01E05 - pt2"


def test_plex_split_movie_name():
    service = NamingProfileService()
    value = service.render_relation_name(
        "plex",
        {
            "relation_type": "split_movie",
            "part_number": 1,
        },
        title="Film",
        year="2001",
    )
    assert value == "Film (2001) - pt1"


def test_sample_relation_is_not_actionable(tmp_path: Path):
    root = tmp_path / "Sample"
    root.mkdir()
    sample = root / "Show-S01E01-sample.mkv"
    sample.write_text("x", encoding="utf-8")

    item = type("Item", (), {})()
    item.path = sample
    item.media_type = "series"
    item.episode = "01"
    item.season = "01"
    item.detection_data = {}

    relation = MediaRelationEngine().analyze_item(item)
    assert relation.relation_type == "sample"
    assert relation.recommended_action == "keep"
    assert relation.review_required is False
