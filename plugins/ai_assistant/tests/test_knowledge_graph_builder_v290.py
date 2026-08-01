import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_graph_builder import KnowledgeGraphBuilder

def result():
    return KnowledgeGraphBuilder().build(
        source={"id": "wiki", "name": "Wikipedia"},
        parser_result={"result": {"fields": {
            "title": "Aquaman: Lost Kingdom", "media_type": "movie"
        }}},
        semantic_result={"primary_entity_type": "movie", "primary_entity_confidence": 0.84},
        classified_fields={"primary_values": {
            "release_year": 2023,
            "predecessor": {"title": "Aquaman", "year": 2018},
            "universe": "DC Extended Universe",
            "universe_transition_year": 2024,
        }},
        scan_result={"text_preview": (
            "Originaltitel Aquaman and the Lost Kingdom Produktionsland USA "
            "Länge 124 Minuten FSK 12 Regie James Wan "
            "Drehbuch David Leslie Johnson Musik Rupert Gregson-Williams "
            "Kamera Don Burgess Schnitt Kirk M. Morri"
        )},
    )

def test_nodes_and_edges():
    data = result()
    keys = {n["key"] for n in data["nodes"]}
    types = {e["edge_type"] for e in data["edges"]}
    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "movie:aquaman:2018" in keys
    assert {"sequel_of", "belongs_to", "ends_with"} <= types

def test_metadata_and_crew():
    data = result()
    main = next(n for n in data["nodes"] if n["key"] == data["main_node_key"])
    types = {e["edge_type"] for e in data["edges"]}
    assert main["metadata"]["runtime_minutes"] == 124
    assert main["metadata"]["fsk"] == 12
    assert main["metadata"]["original_title"] == "Aquaman and the Lost Kingdom"
    assert {"directed_by", "music_by", "cinematography_by"} <= types
