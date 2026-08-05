from pathlib import Path

from services.learning_store import LearningStore
from services.profile_service import ProfileService


def test_profiles_are_loadable():
    root = Path(__file__).resolve().parents[1]
    service = ProfileService(root)
    ids = {profile["id"] for profile in service.list_profiles()}

    assert {"standard", "plex", "jellyfin", "emby", "kodi", "audiobook"} <= ids


def test_learning_only_suggests_after_threshold(tmp_path: Path):
    store = LearningStore(tmp_path, threshold=3)

    assert store.record("Film 2024", "Film (2024)")["suggest_rule"] is False
    assert store.record("Film 2024", "Film (2024)")["suggest_rule"] is False
    result = store.record("Film 2024", "Film (2024)")

    assert result["suggest_rule"] is True
    assert len(store.suggestions()) == 1
