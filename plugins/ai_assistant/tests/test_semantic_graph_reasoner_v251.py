import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine import KnowledgeEngine
from services.knowledge_engine.semantic_graph_reasoner import SemanticGraphReasoner


def _types(result):
    return {
        item["relation_type"]
        for item in result["proposals"]
        if item["kind"] == "direct_relation"
    }


def test_prequel_spin_off_backdoor_and_reboot(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity({"title": "Hauptserie", "media_type": "series", "year": 2000})
    engine.upsert_identity({"title": "Hauptserie Origins", "media_type": "series", "year": 2024, "metadata": {"parent_title": "Hauptserie", "is_prequel": True}})
    engine.upsert_identity({"title": "Nebenserie", "media_type": "series", "year": 2005, "metadata": {"parent_title": "Hauptserie", "is_spin_off": True}})
    engine.upsert_identity({"title": "Pilotfolge", "media_type": "episode", "year": 2004, "metadata": {"parent_title": "Hauptserie", "is_backdoor_pilot": True}})
    engine.upsert_identity({"title": "Hauptserie Reboot", "media_type": "series", "year": 2025, "metadata": {"parent_title": "Hauptserie", "is_reboot": True}})
    assert {"prequel", "spin_off", "backdoor_pilot", "reboot"} <= _types(SemanticGraphReasoner(engine).reason())


def test_crossover_metadata(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity({"title": "Serie A", "media_type": "series", "metadata": {"crossover_with": ["Serie B"]}})
    engine.upsert_identity({"title": "Serie B", "media_type": "series"})
    result = SemanticGraphReasoner(engine).reason()
    crossovers = [x for x in result["proposals"] if x.get("relation_type") == "crossover"]
    assert len(crossovers) == 1
    assert crossovers[0]["confidence"] >= 0.9


def test_shared_characters_and_universe(tmp_path):
    engine = KnowledgeEngine(tmp_path)
    engine.upsert_identity({"title": "Serie A", "media_type": "series", "metadata": {"universe": "Test", "shared_characters": ["Figur X"]}})
    engine.upsert_identity({"title": "Serie B", "media_type": "series", "metadata": {"universe": "Test", "shared_characters": ["Figur X"]}})
    related = [x for x in SemanticGraphReasoner(engine).reason()["proposals"] if x.get("relation_type") == "related"]
    assert related
    assert related[0]["confidence"] >= 0.72
