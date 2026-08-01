import sqlite3
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.fingerprint_store import FingerprintReferenceStore
from services.knowledge_learning import KnowledgeLearningService
from services.semantic_identity import IdentityCandidateBuilder
from services.visual_knowledge import VisualKnowledgeStore


def _analysis(fingerprint="abc123", visual_signature=None):
    visual = {"visual_signature": visual_signature, "ocr_logo_fusion": {"candidates": []}}
    return {
        "identification": {
            "media_type": "unknown",
            "title_candidate": "bad filename",
            "confidence": 0.4,
        },
        "online": {"ranking": {"matches": []}},
        "in_video": {
            "agents": {
                "fingerprint_agent": {
                    "state": "completed",
                    "video_fingerprint": fingerprint,
                }
            },
            "visual_intelligence": visual,
        },
    }


def test_raw_fingerprint_does_not_become_identity_evidence(tmp_path):
    builder = IdentityCandidateBuilder(tmp_path / "knowledge.sqlite3")
    result = builder.build(_analysis())
    assert result["candidate_count"] == 1
    assert result["best_candidate"]["independent_groups"] == ["filename"]


def test_registered_fingerprint_creates_identity_candidate(tmp_path):
    db = tmp_path / "knowledge.sqlite3"
    FingerprintReferenceStore(db).register(
        "abc123",
        {
            "media_type": "movie",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
            "confidence": 1.0,
        },
    )
    result = IdentityCandidateBuilder(db).build(_analysis())
    titles = {item["title"] for item in result["candidates"]}
    assert "Aquaman and the Lost Kingdom" in titles
    aquaman = next(item for item in result["candidates"] if item["title"] == "Aquaman and the Lost Kingdom")
    assert "fingerprint" in aquaman["independent_groups"]


def test_visual_knowledge_resolves_confirmed_identity(tmp_path):
    db = tmp_path / "knowledge.sqlite3"
    learning = KnowledgeLearningService(db)
    learned = learning.confirm(
        {
            "identification": {"title_candidate": "wrong"},
            "file": {"name": "wrong.mkv"},
            "in_video": {"agents": {}},
        },
        {
            "media_type": "movie",
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
        },
    )
    VisualKnowledgeStore(db).register_confirmed(
        learned["identity_id"],
        {"visual_signature": "visual-123"},
    )
    result = IdentityCandidateBuilder(db).build(
        _analysis(fingerprint="not-known", visual_signature="visual-123")
    )
    aquaman = next(item for item in result["candidates"] if item["title"] == "Aquaman and the Lost Kingdom")
    assert "visual" in aquaman["independent_groups"]
