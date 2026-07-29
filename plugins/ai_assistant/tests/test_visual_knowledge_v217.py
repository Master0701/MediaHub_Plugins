import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.visual_knowledge import VisualKnowledgeStore


def _visual():
    return {
        "visual_signature": "abc123",
        "visual_fingerprint": {
            "algorithm": "multi-frame-dhash-profile-v1",
            "frame_count": 4,
        },
        "scene_signature": {
            "algorithm": "normalized-scene-rhythm-visual-v1",
            "segment_count": 12,
        },
        "ocr_logo_fusion": {
            "best_title": "STAR TREK",
            "best_score": 0.95,
        },
        "intro_outro_detection": {
            "intro": {"detected": True, "confidence": 0.88},
            "outro": {"detected": True, "confidence": 0.71},
        },
        "character_preparation": {
            "anonymous_subject_count": 3,
            "recurring_subject_count": 1,
        },
    }


def test_unconfirmed_visual_knowledge_is_not_persisted(tmp_path):
    store = VisualKnowledgeStore(tmp_path / "knowledge.sqlite3")
    result = store.register_confirmed(
        1,
        _visual(),
        confirmed_by_user=False,
    )

    assert result["persisted"] is False
    assert store.for_identity(1) == []


def test_confirmed_visual_knowledge_roundtrips(tmp_path):
    store = VisualKnowledgeStore(tmp_path / "knowledge.sqlite3")
    result = store.register_confirmed(7, _visual())

    assert result["persisted"] is True
    rows = store.for_identity(7)
    assert len(rows) == 1
    assert rows[0]["visual_fingerprint"]["frame_count"] == 4
    assert rows[0]["ocr_logo_fusion"]["best_title"] == "STAR TREK"


def test_signature_lookup_and_export(tmp_path):
    store = VisualKnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.register_confirmed(7, _visual())

    matches = store.find_by_signature("abc123")
    snapshot = store.export_snapshot()

    assert matches[0]["identity_id"] == 7
    assert snapshot["type"] == "visual_knowledge_snapshot"
    assert snapshot["entries"][0]["visual_signature"] == "abc123"
