import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.completeness import (
    KnowledgeGraphCompletenessService,
)


def test_saved_order_is_checked_as_complete_group(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    first = engine.create_entity("Aquaman", "movie", year=2018)
    second = engine.create_entity(
        "Aquaman and the Lost Kingdom",
        "movie",
        year=2023,
    )
    engine.create_order(
        "Aquaman – Veröffentlichungsreihenfolge",
        "release",
        [first["id"], second["id"]],
    )

    result = KnowledgeGraphCompletenessService(engine).analyze()

    assert result["group_count"] == 1
    group = result["groups"][0]
    assert group["group_type"] == "order"
    assert group["complete"] is True
    assert group["missing_count"] == 0


def test_relation_group_is_detected(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    movie = engine.create_entity("Aquaman", "movie", year=2018)
    franchise = engine.create_entity(
        "Aquaman",
        "franchise",
    )
    engine.connect(
        movie["id"],
        franchise["id"],
        "franchise",
    )

    result = KnowledgeGraphCompletenessService(engine).analyze()

    assert result["group_count"] == 1
    assert result["groups"][0]["group_type"] == "franchise"
    assert result["groups"][0]["member_count"] == 1


def test_readable_display_uses_titles_not_raw_relation_ids():
    text = (
        PLUGIN_DIR / "plugin.py"
    ).read_text(encoding="utf-8")

    assert "source_label" in text
    assert "target_label" in text
    assert "VORHANDEN:" in text
    assert "Status: " in text
    assert 'lines.append(f"  {position}. {label}")' in text
