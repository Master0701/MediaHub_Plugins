import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_learning import KnowledgeLearningService
from services.learning_status import LearningStatusService


def _analysis():
    return {
        "file": {
            "name": "abc123.mkv",
            "path": r"D:\Videos\abc123.mkv",
        },
        "identification": {
            "media_type": "unknown",
            "title_candidate": "abc123",
        },
        "in_video": {
            "agents": {
                "fingerprint_agent": {
                    "video_fingerprint": "fingerprint-227-test-value",
                }
            },
            "visual_intelligence": {
                "visual_signature": "visual-signature-227",
                "visual_fingerprint": {"frame_count": 3},
                "scene_signature": {"segment_count": 8},
                "ocr_logo_fusion": {"best_title": "AQUAMAN"},
                "intro_outro_detection": {
                    "intro": {"detected": True},
                    "outro": {"detected": True},
                },
                "character_preparation": {
                    "anonymous_subject_count": 2,
                },
            },
        },
    }


def test_confirmation_persists_fingerprint_and_visual_knowledge(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    service = KnowledgeLearningService(database)

    result = service.confirm(
        _analysis(),
        {
            "media_type": "movie",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
        },
    )

    assert result["fingerprint_detected"] is True
    assert result["fingerprint"]["title"] == "Aquaman and the Lost Kingdom"
    assert result["visual_knowledge_detected"] is True
    assert result["visual_knowledge"]["visual_signature"] == "visual-signature-227"
    assert result["database_path"] == str(database.resolve())


def test_learning_status_reports_same_database(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    KnowledgeLearningService(database).confirm(
        _analysis(),
        {
            "media_type": "movie",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
        },
    )

    status = LearningStatusService(database).status()

    assert status["database_path"] == str(database.resolve())
    assert status["learned_identity_count"] == 1
    assert status["fingerprint_reference_count"] == 1
    assert status["visual_knowledge_count"] == 1
