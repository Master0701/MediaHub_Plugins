import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine, RelationType


def test_infers_spin_off_from_backdoor_pilot_chain(tmp_path):
    engine=KnowledgeEngine(tmp_path)
    fire=engine.create_entity("Chicago Fire","series")
    episode=engine.create_entity("S03E19","episode")
    med=engine.create_entity("Chicago Med","series")
    engine.connect(episode["id"],fire["id"],RelationType.EPISODE_OF.value)
    engine.connect(med["id"],episode["id"],RelationType.STARTS_IN_EPISODE.value)
    result=engine.infer_relations("Chicago Med")
    assert any(x.get("relation_type")==RelationType.SPIN_OFF.value for x in result["suggestions"])
    assert all(x.get("requires_confirmation") is not None for x in result["suggestions"])


def test_inference_is_not_persisted(tmp_path):
    engine=KnowledgeEngine(tmp_path)
    a=engine.create_entity("A","series"); b=engine.create_entity("B","series"); c=engine.create_entity("C","series")
    engine.connect(a["id"],b["id"],RelationType.SPIN_OFF.value)
    engine.connect(b["id"],c["id"],RelationType.SEQUEL.value)
    before=len(engine.store.all_relations())
    result=engine.infer_relations(a["id"])
    assert result["persisted"] is False
    assert len(engine.store.all_relations())==before


def test_export_contains_intelligence_and_audiobooks(tmp_path):
    engine=KnowledgeEngine(tmp_path)
    book=engine.create_entity("Test Hörbuch","audiobook")
    snapshot=engine.export_snapshot(book["id"])
    assert snapshot["producer_version"]=="1.9.0"
    assert "intelligence" in snapshot
    assert "audiobook" in snapshot["supports_media_types"]
