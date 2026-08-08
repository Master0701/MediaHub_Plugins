from pathlib import Path

import pytest

from services.media_scanner import MediaScanner
from services.naming_profiles import NamingProfileService
from services.relation_preview_service import RelationPreviewService


def test_builtin_profiles_available():
    service = NamingProfileService()
    ids = {profile.profile_id for profile in service.list_profiles()}
    assert {"plex", "jellyfin", "emby", "kodi"} <= ids


def test_custom_profile_persists(tmp_path: Path):
    storage = tmp_path / "profiles.json"
    service = NamingProfileService(storage)
    service.save_custom_profile(
        profile_id="meinprofil",
        display_name="Mein Profil",
        multi_episode_template="{title} S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} S{season}E{episode_start} Teil {part_number}",
        split_movie_template="{title} ({year}) Teil {part_number}",
    )

    loaded = NamingProfileService(storage)
    profile = loaded.get_profile("meinprofil")
    assert profile.display_name == "Mein Profil"
    assert profile.builtin is False


def test_builtin_profile_cannot_be_overwritten(tmp_path: Path):
    service = NamingProfileService(tmp_path / "profiles.json")
    with pytest.raises(ValueError):
        service.save_custom_profile(
            profile_id="plex",
            display_name="Falsch",
            multi_episode_template="{title}",
            split_episode_template="{title}",
            split_movie_template="{title}",
        )


def test_builtin_profile_cannot_be_deleted(tmp_path: Path):
    service = NamingProfileService(tmp_path / "profiles.json")
    with pytest.raises(ValueError):
        service.delete_custom_profile("plex")


def test_relation_preview_multi_episode_plex(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    path = root / "CSI Las Vegas - S03E10-E11.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])
    preview = RelationPreviewService().build_preview(
        items[0],
        profile_id="plex",
    )

    assert preview.relation_type == "multi_episode"
    assert preview.profile_id == "plex"
    assert preview.suggested_name.endswith("S03E10-E11.mkv")
    assert preview.review_required is True
    assert "manuell_pruefen" in preview.options


def test_relation_preview_split_episode(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    path = root / "CSI Las Vegas - S05E12 - pt1.mkv"
    path.write_text("x", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])
    preview = RelationPreviewService().build_preview(items[0])

    assert preview.relation_type == "split_episode"
    assert preview.suggested_name.endswith("S05E12 - pt1.mkv")
    assert "merge_kandidat" in preview.options


def test_relation_preview_missing_candidate_does_not_claim_missing(tmp_path: Path):
    root = tmp_path / "Serie"
    root.mkdir()
    (root / "Show - S01E01.mkv").write_text("1", encoding="utf-8")
    (root / "Show - S01E03.mkv").write_text("3", encoding="utf-8")

    items, _ = MediaScanner().scan([{"path": str(root)}])
    preview = RelationPreviewService().build_preview(items[0])

    assert preview.relation_type == "single"
    assert preview.review_required is True
    assert any(
        "beweist weder" in warning
        for warning in preview.warnings
    )
    assert "in_multi_episode_enthalten_pruefen" in preview.options


def test_custom_profile_renders_relation(tmp_path: Path):
    service = NamingProfileService(tmp_path / "profiles.json")
    service.save_custom_profile(
        profile_id="custom",
        display_name="Custom",
        multi_episode_template="{title} [{season}x{episode_start}-{episode_end}]",
        split_episode_template="{title} [{season}x{episode_start}] Datei {part_number}",
        split_movie_template="{title} ({year}) Datei {part_number}",
    )

    value = service.render_relation_name(
        "custom",
        {
            "relation_type": "multi_episode",
            "episode_start": "05",
            "episode_end": "06",
        },
        title="Show",
        season="1",
    )
    assert value == "Show [01x05-06]"


def test_invalid_custom_template_rejected(tmp_path: Path):
    service = NamingProfileService(tmp_path / "profiles.json")
    with pytest.raises(ValueError):
        service.save_custom_profile(
            profile_id="bad",
            display_name="Bad",
            multi_episode_template="kein titel",
            split_episode_template="{title}",
            split_movie_template="{title}",
        )
