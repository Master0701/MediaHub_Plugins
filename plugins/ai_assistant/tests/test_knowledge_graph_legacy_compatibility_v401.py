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
            "title": "Aquaman: Lost Kingdom",
            "media_type": "movie",
        }}},
        semantic_result={
            "primary_entity_type": "movie",
            "primary_entity_confidence": 0.84,
        },
        classified_fields={"primary_values": {
            "release_year": 2023,
            "predecessor": {"title": "Aquaman", "year": 2018},
            "universe": "DC Extended Universe",
            "universe_transition_year": 2024,
        }},
        scan_result={"text_preview": (
            "Originaltitel Aquaman and the Lost Kingdom "
            "Produktionsland USA Länge 124 Minuten FSK 12 "
            "Regie James Wan Drehbuch David Leslie Johnson "
            "Musik Rupert Gregson-Williams "
            "Kamera Don Burgess Schnitt Kirk M. Morri"
        )},
    )


def test_legacy_nodes_and_edges():
    data = result()
    keys = {item["key"] for item in data["nodes"]}
    edge_types = {item["edge_type"] for item in data["edges"]}

    assert "movie:aquaman: lost kingdom:2023" in keys
    assert "movie:aquaman:2018" in keys
    assert "universe:dc extended universe" in keys
    assert "event:universumswechsel 2024:2024" in keys
    assert "person:james wan" in keys
    assert "person:rupert gregson-williams" in keys
    assert "person:don burgess" in keys

    assert {
        "sequel_of",
        "belongs_to",
        "ends_with",
        "directed_by",
        "music_by",
        "cinematography_by",
    } <= edge_types


def test_legacy_metadata_is_preserved():
    data = result()
    main = next(
        item
        for item in data["nodes"]
        if item["key"] == data["main_node_key"]
    )

    assert main["year"] == 2023
    assert main["metadata"]["runtime_minutes"] == 124
    assert main["metadata"]["fsk"] == 12
    assert (
        main["metadata"]["original_title"]
        == "Aquaman and the Lost Kingdom"
    )


def test_new_group_api_still_works():
    data = KnowledgeGraphBuilder.build(
        node_groups=[[{
            "node_type": "character",
            "title": "Arthur Curry",
            "key": "character:arthur curry",
        }]],
        edge_groups=[],
        source={"id": "wiki"},
    )

    assert data["strategy"] == "knowledge_graph_builder_v402"
    assert data["statistics"]["node_count"] == 1

