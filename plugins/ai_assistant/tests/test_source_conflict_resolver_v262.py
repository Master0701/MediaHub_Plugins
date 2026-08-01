import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.source_conflict_resolver import SourceConflictResolver


def _results():
    return [
        {
            "source": {
                "id": "tmdb",
                "name": "TMDb",
                "trust": 0.96,
                "priority": 100,
            },
            "values": {
                "title": "Aquaman and the Lost Kingdom",
                "year": 2023,
                "media_type": "movie",
            },
        },
        {
            "source": {
                "id": "wiki",
                "name": "Wikipedia",
                "trust": 0.84,
                "priority": 70,
            },
            "values": {
                "title": "Aquaman and the Lost Kingdom",
                "year": 2023,
                "media_type": "film",
            },
        },
    ]


def test_conflicts_are_detected_field_by_field(tmp_path):
    resolver = SourceConflictResolver(tmp_path / "knowledge.sqlite3")
    result = resolver.compare(_results())

    assert result["field_count"] == 3
    assert result["conflict_count"] == 1
    media_type = next(
        item
        for item in result["fields"]
        if item["field"] == "media_type"
    )
    assert media_type["has_conflict"] is True
    assert media_type["recommended_value"] == "movie"


def test_matching_values_gain_multiple_supporters(tmp_path):
    resolver = SourceConflictResolver(tmp_path / "knowledge.sqlite3")
    result = resolver.compare(_results())

    title = next(
        item
        for item in result["fields"]
        if item["field"] == "title"
    )
    assert title["has_conflict"] is False
    assert title["candidates"][0]["support_count"] == 2


def test_confirmed_fields_are_persistent(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    resolver = SourceConflictResolver(database)
    comparison = resolver.compare(_results())
    decision = resolver.confirm_fields(
        comparison["id"],
        {
            "title": "Aquaman and the Lost Kingdom",
            "year": 2023,
        },
        target_entity_id="entity-1",
    )

    reopened = SourceConflictResolver(database)
    assert decision["status"] == "confirmed"
    assert reopened.status()["decision_count"] == 1
