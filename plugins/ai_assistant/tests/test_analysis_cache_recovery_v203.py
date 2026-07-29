import sqlite3
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.analysis_cache import AnalysisCache


def test_creates_missing_table_and_roundtrips_analysis(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    video = tmp_path / "film.mkv"
    video.write_bytes(b"video-data")

    cache = AnalysisCache(database)
    cache.put(
        video,
        {
            "identification": {
                "title_candidate": "Testfilm",
                "confidence": 0.5,
            },
            "decision": {"confidence": 0.75},
            "methods_used": ["filename", "ffprobe"],
            "in_video": {
                "agents": {
                    "fingerprint_agent": {
                        "video_fingerprint": "a" * 64
                    }
                }
            },
        },
    )

    loaded = cache.get(video)

    assert loaded is not None
    assert (
        loaded["in_video"]["agents"]["fingerprint_agent"][
            "video_fingerprint"
        ]
        == "a" * 64
    )

    with sqlite3.connect(database) as db:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "identification_cache" in tables


def test_repairs_existing_database_without_cache_table(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE existing_data(id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO existing_data(id) VALUES (1)")
        db.commit()

    cache = AnalysisCache(database)

    with sqlite3.connect(database) as db:
        existing = db.execute(
            "SELECT COUNT(*) FROM existing_data"
        ).fetchone()[0]
        cache_table = db.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table' AND name='identification_cache'
            """
        ).fetchone()[0]

    assert existing == 1
    assert cache_table == 1


def test_clear_methods_are_compatible(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    first = tmp_path / "one.mkv"
    second = tmp_path / "two.mkv"
    first.write_bytes(b"one")
    second.write_bytes(b"two")

    cache = AnalysisCache(database)
    cache.put(first, {"methods_used": []})
    cache.put(second, {"methods_used": []})

    assert cache.clear_for(first) == 1
    assert cache.get(first) is None
    assert cache.get(second) is not None
    assert cache.clear() == 1
