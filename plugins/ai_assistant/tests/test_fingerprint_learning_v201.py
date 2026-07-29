import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_learning import KnowledgeLearningService


def _identity():
    return {
        "title": "Aquaman Lost Kingdom",
        "media_type": "movie",
        "year": 2023,
        "aliases": ["PSO", "pso aqua2 ts"],
    }


def test_finds_normal_top_level_fingerprint(tmp_path):
    service = KnowledgeLearningService(tmp_path / "knowledge.sqlite3")
    analysis = {
        "file": {"path": "X:/film.mkv", "name": "film.mkv"},
        "identification": {"title_candidate": "pso aqua2 ts"},
        "in_video": {
            "agents": {
                "fingerprint_agent": {
                    "state": "completed",
                    "video_fingerprint": "a" * 64,
                }
            }
        },
    }

    result = service.confirm(analysis, _identity())

    assert result["fingerprint_detected"] is True
    assert result["fingerprint"]["fingerprint"] == "a" * 64
    assert service.fingerprints.lookup("a" * 64)["title"] == "Aquaman Lost Kingdom"


def test_finds_fingerprint_inside_orchestrator_cache_result(tmp_path):
    service = KnowledgeLearningService(tmp_path / "knowledge.sqlite3")
    analysis = {
        "identification": {"title_candidate": "pso aqua2 ts"},
        "orchestration": {
            "plan": {
                "steps": [
                    {
                        "id": "basic_analysis",
                        "result": {
                            "file": {"path": "X:/cached-film.mkv"},
                            "in_video": {
                                "agents": {
                                    "fingerprint_agent": {
                                        "video_fingerprint": "b" * 64
                                    }
                                }
                            },
                        },
                    }
                ]
            }
        },
    }

    result = service.confirm(analysis, _identity())

    assert result["fingerprint_detected"] is True
    assert "fingerprint_agent" in result["fingerprint_source"]
    assert result["fingerprint"]["fingerprint"] == "b" * 64
    assert result["fingerprint"]["source_path"] == "X:/cached-film.mkv"


def test_no_fingerprint_is_reported_honestly(tmp_path):
    service = KnowledgeLearningService(tmp_path / "knowledge.sqlite3")
    result = service.confirm(
        {"identification": {"title_candidate": "pso aqua2 ts"}},
        _identity(),
    )

    assert result["fingerprint_detected"] is False
    assert result["fingerprint"] is None
    assert result["fingerprint_source"] is None
