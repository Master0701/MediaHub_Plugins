import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_works_with_and_rescue_relations():
    text = (
        "David Kane arbeitet mit Stephen Shin zusammen. "
        "Mera rettete Arthur Curry."
    )
    result = RelationshipIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "works_with" in edge_types
    assert "rescues" in edge_types
    assert "rescued_by" in edge_types


def test_kidnap_and_fight_relations():
    text = (
        "David Kane entführte Arthur Jr. "
        "Arthur Curry kämpft gegen David Kane."
    )
    result = RelationshipIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "kidnaps" in edge_types
    assert "kidnapped_by" in edge_types
    assert "fights_with" in edge_types


def test_artifact_creation_and_find_relations():
    text = (
        "Der schwarze Dreizack wurde von Kordax erschaffen. "
        "David Kane findet einen schwarzen Dreizack."
    )
    result = RelationshipIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "artifact:schwarze dreizack" in keys
    assert "character:kordax" in keys
    assert "created_by" in edge_types
    assert "creates" in edge_types
    assert "finds" in edge_types


def test_alias_from_plot_sentence():
    result = RelationshipIntelligence().analyze(
        text="Arthur Curry alias Aquaman verteidigte Atlantis.",
        source=SOURCE,
    )

    assert any(
        edge["edge_type"] == "alias_of"
        and edge["source_node_key"] == "character_alias:aquaman"
        and edge["target_node_key"] == "character:arthur curry"
        for edge in result["edges"]
    )
