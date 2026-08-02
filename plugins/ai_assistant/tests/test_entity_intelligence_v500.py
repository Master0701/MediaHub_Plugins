import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.entity_intelligence import EntityIntelligence


def test_detects_explicit_entity_types_and_media_appearances():
    result = EntityIntelligence.analyze(
        main_node={"key": "series:doctor-who", "node_type": "series", "title": "Doctor Who"},
        text=(
            "Die TARDIS ist eine Zeitmaschine. "
            "Die Sternenflotte ist eine Organisation. "
            "Vulkan ist ein Planet."
        ),
        source={"id": "source-1"},
    )
    node_types = {item["node_type"] for item in result["nodes"]}
    edge_types = {item["edge_type"] for item in result["edges"]}
    assert {"technology", "organization", "planet"} <= node_types
    assert "appears_in" in edge_types
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True


def test_detects_german_entity_relations():
    result = EntityIntelligence.analyze(
        main_node={"key": "series:test", "node_type": "series", "title": "Test"},
        text=(
            "Gotham City liegt in New Jersey. "
            "Vulkan ist die Heimatwelt von Vulkanier. "
            "Mjölnir wird benutzt von Thor."
        ),
        source={"id": "source-2"},
    )
    edge_types = {item["edge_type"] for item in result["edges"]}
    assert {"located_in", "homeworld_of", "used_by"} <= edge_types


def test_detects_english_entity_relations():
    result = EntityIntelligence.analyze(
        main_node={"key": "movie:test", "node_type": "movie", "title": "Test"},
        text=(
            "USS Enterprise is operated by Starfleet. "
            "Data was created by Doctor Soong."
        ),
        source={"id": "source-3"},
    )
    edge_types = {item["edge_type"] for item in result["edges"]}
    assert {"operated_by", "created_by"} <= edge_types
