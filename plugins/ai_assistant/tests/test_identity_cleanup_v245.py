import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.identity_cleanup import (
    IdentityCleanupService,
)


def test_graph_entity_can_be_merged_with_backup(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    engine = KnowledgeEngine(database)
    source = engine.create_entity(
        "Aquaman and the Lost Kingdom",
        "movie",
        year=2018,
        aliases=["falsch"],
    )
    target = engine.create_entity(
        "Aquaman and the Lost Kingdom",
        "movie",
        year=2023,
        aliases=["richtig"],
    )

    service = IdentityCleanupService(database, engine.store)
    result = service.apply(source["id"], target["id"])

    assert result["status"] == "completed"
    assert result["mode"] == "merge"
    assert Path(result["backup"]["backup_dir"]).is_dir()
    assert engine.store.get_entity(source["id"]) is None
    kept = engine.store.get_entity(target["id"])
    assert "falsch" in kept["aliases"]


def test_graph_entity_can_be_deleted(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    engine = KnowledgeEngine(database)
    source = engine.create_entity("Falsch", "movie", year=2023)

    result = IdentityCleanupService(
        database,
        engine.store,
    ).apply(source["id"])

    assert result["mode"] == "delete"
    assert engine.store.get_entity(source["id"]) is None


def test_preview_requires_confirmation_and_backup(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    engine = KnowledgeEngine(database)
    source = engine.create_entity("Falsch", "movie")

    preview = IdentityCleanupService(
        database,
        engine.store,
    ).preview(source["id"])

    assert preview["backup_required"] is True
    assert preview["requires_user_confirmation"] is True
