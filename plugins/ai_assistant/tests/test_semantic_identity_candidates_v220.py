import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.semantic_identity import IdentityCandidateBuilder


def test_builder_keeps_filename_candidate_without_deciding(tmp_path):
    result = IdentityCandidateBuilder(tmp_path / "knowledge.sqlite3").build({
        "identification": {"title_candidate": "Aquaman", "media_type": "movie", "confidence": 0.4},
        "online": {"ranking": {"matches": []}},
        "in_video": {"agents": {}, "visual_intelligence": {}},
    })
    assert result["decision_made"] is False
    assert result["candidate_count"] == 1
    assert result["best_candidate"]["title"] == "Aquaman"
    assert result["best_candidate"]["stage"] == "candidate"


def test_builder_merges_online_and_learned_alias_evidence(tmp_path):
    builder = IdentityCandidateBuilder(tmp_path / "knowledge.sqlite3")
    builder.knowledge.confirm(
        {"identification": {"title_candidate": "aqua2"}, "file": {"name": "aqua2.mkv"}},
        {"title": "Aquaman and the Lost Kingdom", "media_type": "movie", "year": 2023, "aliases": ["aqua2"]},
    )
    result = builder.build({
        "identification": {"title_candidate": "aqua2", "media_type": "unknown", "confidence": 0.4},
        "online": {"ranking": {"matches": [{
            "title": "Aquaman and the Lost Kingdom", "media_type": "movie", "year": 2023,
            "score": 0.86, "provider_name": "TestProvider", "aliases": ["aqua2"]
        }]}},
        "in_video": {"agents": {}, "visual_intelligence": {}},
    })
    target = next(item for item in result["candidates"] if item["title"] == "Aquaman and the Lost Kingdom")
    assert target["source_count"] == 2
    assert target["candidate_score"] > 0.7


def test_low_quality_visual_text_is_not_candidate(tmp_path):
    result = IdentityCandidateBuilder(tmp_path / "knowledge.sqlite3").build({
        "identification": {}, "online": {"ranking": {"matches": []}},
        "in_video": {"agents": {}, "visual_intelligence": {"ocr_logo_fusion": {"candidates": [{
            "text": "ET ur eo", "title_candidate": True, "score": 0.8, "text_quality": 0.3
        }]}}},
    })
    assert result["candidate_count"] == 0
