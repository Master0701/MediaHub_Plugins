import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_intelligence import RelationshipIntelligence


SOURCE = {"id": "wiki"}


def test_all_general_relationships_still_work():
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

    assert {
        "works_with",
        "rescues",
        "rescued_by",
        "kidnaps",
        "kidnapped_by",
        "fights_with",
        "created_by",
        "creates",
    } <= edge_types
