import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine, RelationType


def test_franchise_traversal_and_story_relation(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    fire = engine.create_entity("Chicago Fire", "series")
    episode = engine.create_entity("Chicago Fire S03E19", "episode")
    med = engine.create_entity("Chicago Med", "series")
    engine.connect(episode["id"], fire["id"], RelationType.EPISODE_OF.value)
    engine.connect(med["id"], episode["id"], RelationType.STARTS_IN_EPISODE.value, metadata={"kind": "backdoor_pilot"})
    graph = engine.resolve_franchise("Chicago Med")
    titles = {item["title"] for item in graph["entities"]}
    assert {"Chicago Med", "Chicago Fire S03E19", "Chicago Fire"} <= titles


def test_neighbors_are_direction_aware(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    parent = engine.create_entity("Stargate SG-1", "series")
    child = engine.create_entity("Stargate Atlantis", "series", aliases=["SGA"])
    engine.connect(parent["id"], child["id"], RelationType.SPIN_OFF.value)
    outgoing = engine.neighbors(parent["id"], RelationType.SPIN_OFF.value, direction="outgoing")
    assert [item["title"] for item in outgoing["entities"]] == ["Stargate Atlantis"]


def test_export_snapshot_supports_audiobooks_and_formats(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    book = engine.create_entity("Test Hörbuch", "audiobook")
    snapshot = engine.export_snapshot(book["id"])
    assert snapshot["export_targets"] == ["html", "pdf", "xlsx"]
    assert "audiobook" in snapshot["supports_media_types"]
    assert snapshot["graph"]["root"]["title"] == "Test Hörbuch"

