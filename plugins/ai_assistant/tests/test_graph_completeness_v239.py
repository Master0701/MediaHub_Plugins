import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.completeness import (
    KnowledgeGraphCompletenessService,
)


def test_missing_franchise_entry_is_reported(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity(
        {
            "title": "Aquaman",
            "media_type": "movie",
            "year": 2018,
            "metadata": {
                "franchise": "Aquaman",
                "expected_entries": [
                    "Aquaman",
                    "Aquaman and the Lost Kingdom",
                ],
            },
        }
    )

    result = KnowledgeGraphCompletenessService(engine).analyze()

    assert result["group_count"] == 1
    assert result["missing_count"] == 1
    assert result["groups"][0]["missing"][0]["title"] == (
        "Aquaman and the Lost Kingdom"
    )
    assert result["automatic_changes"] is False


def test_complete_group_has_no_missing_entries(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    expected = ["Teil 1", "Teil 2"]

    for year, title in ((2010, "Teil 1"), (2012, "Teil 2")):
        engine.upsert_identity(
            {
                "title": title,
                "media_type": "movie",
                "year": year,
                "metadata": {
                    "franchise": "Test",
                    "expected_entries": expected,
                },
            }
        )

    result = KnowledgeGraphCompletenessService(engine).analyze()
    group = result["groups"][0]

    assert group["complete"] is True
    assert group["missing_count"] == 0
