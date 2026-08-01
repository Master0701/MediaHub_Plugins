import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_general_rules_keep_numeric_groups():
    text = (
        "David Kane arbeitet mit Stephen Shin zusammen. "
        "Mera rettete Arthur Curry. "
        "David Kane entführte Arthur Jr. "
        "Arthur Curry kämpft gegen David Kane. "
        "Der schwarze Dreizack wurde von Kordax erschaffen."
    )

    result = RelationshipIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "works_with" in edge_types
    assert "rescues" in edge_types
    assert "kidnaps" in edge_types
    assert "fights_with" in edge_types
    assert "created_by" in edge_types


def test_alias_rule_uses_named_groups_only():
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


def test_general_and_alias_rules_work_together():
    text = (
        "Arthur Curry alias Aquaman verteidigte Atlantis. "
        "David Kane arbeitet mit Stephen Shin zusammen."
    )

    result = RelationshipIntelligence().analyze(
        text=text,
        source=SOURCE,
    )

    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "alias_of" in edge_types
    assert "works_with" in edge_types
