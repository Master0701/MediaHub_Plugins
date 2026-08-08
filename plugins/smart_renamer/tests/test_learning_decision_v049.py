from __future__ import annotations

from pathlib import Path

from plugin import MediaHubSmartRenamerPlugin
from services.learning_store import LearningStore
from services.media_scanner import MediaScanner


def test_learning_decision_is_persisted_and_returns_hints(tmp_path: Path):
    store = LearningStore(tmp_path)

    saved = store.record_decision(
        tmp_path / "Batman.mkv",
        candidate_id="local-video-unknown",
        media_type="unknown",
        title="Batman",
    )

    assert saved["automatic_application"] is False

    hints = store.decision_hints_for(tmp_path / "Batman.mkv")
    assert hints["learning_match"] is True
    assert hints["preferred_candidate_id"] == "local-video-unknown"
    assert hints["preferred_media_type"] == "unknown"
    assert hints["preferred_title"] == "Batman"


def test_learning_does_not_generalize_to_other_title(tmp_path: Path):
    store = LearningStore(tmp_path)
    store.record_decision(
        tmp_path / "Batman.mkv",
        media_type="movie",
        title="Batman",
    )

    assert store.decision_hints_for(tmp_path / "Superman.mkv") == {}


def test_fingerprint_normalizes_case_dots_and_underscores(tmp_path: Path):
    store = LearningStore(tmp_path)
    store.record_decision(
        tmp_path / "Film_Name.mkv",
        media_type="movie",
        title="Film Name",
    )

    hints = store.decision_hints_for(tmp_path / "film.name.mkv")
    assert hints["preferred_media_type"] == "movie"


def test_existing_schema1_learning_file_is_migrated_safely(tmp_path: Path):
    path = tmp_path / "config" / "smart_renamer_learning.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema_version":1,"patterns":{"x":{"original":"a","corrected":"b","count":3,"promoted":false}}}',
        encoding="utf-8",
    )

    store = LearningStore(tmp_path)
    assert len(store.suggestions()) == 1

    store.record_decision(
        tmp_path / "Film.mkv",
        media_type="movie",
        title="Film",
    )

    content = path.read_text(encoding="utf-8")
    assert '"schema_version": 2' in content
    assert '"patterns"' in content
    assert '"decisions"' in content


def test_learned_hint_changes_decision_ranking_for_same_file(tmp_path: Path):
    path = tmp_path / "Titel.mp3"
    path.write_text("x", encoding="utf-8")

    store = LearningStore(tmp_path)
    first, _ = MediaScanner(
        decision_hint_provider=store.decision_hints_for
    ).scan([{"path": str(path)}])

    candidates = first[0].detection_data["candidates"]
    audiobook = next(
        item for item in candidates
        if item["media_type"] == "audiobook"
    )

    store.record_decision(
        path,
        candidate_id=audiobook["candidate_id"],
        media_type="audiobook",
        title=audiobook["title"],
    )

    second, _ = MediaScanner(
        decision_hint_provider=store.decision_hints_for
    ).scan([{"path": str(path)}])

    decision = second[0].detection_data["decision"]
    assert decision["hints_used"]["learning_match"] is True
    assert decision["hints_used"]["preferred_media_type"] == "audiobook"


def test_call_specific_hints_override_learned_hints(tmp_path: Path):
    path = tmp_path / "Titel.mp3"
    path.write_text("x", encoding="utf-8")
    store = LearningStore(tmp_path)
    store.record_decision(
        path,
        media_type="audiobook",
        title="Titel",
    )

    scanned, _ = MediaScanner(
        decision_hint_provider=store.decision_hints_for
    ).scan([
        {
            "path": str(path),
            "decision_hints": {
                "preferred_media_type": "music",
            },
        }
    ])

    hints = scanned[0].detection_data["decision"]["hints_used"]
    assert hints["preferred_media_type"] == "music"
    assert hints["learning_match"] is True


def test_plugin_learning_api_stays_preview_only(tmp_path: Path):
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1],
    )
    plugin.base_dir = tmp_path
    plugin.learning_store = LearningStore(tmp_path)
    plugin.preview_service.pipeline.scanner.decision_hint_provider = (
        plugin.learning_store.decision_hints_for
    )

    result = plugin.record_detection_decision(
        str(tmp_path / "Film.mkv"),
        media_type="movie",
        title="Film",
    )

    assert result["automatic_application"] is False
    assert plugin.get_learned_decisions()[0]["media_type"] == "movie"


def test_learned_decision_can_be_deleted(tmp_path: Path):
    store = LearningStore(tmp_path)
    path = tmp_path / "Film.mkv"
    store.record_decision(path, media_type="movie", title="Film")

    assert store.delete_decision(path) is True
    assert store.decision_hints_for(path) == {}
    assert store.delete_decision(path) is False
