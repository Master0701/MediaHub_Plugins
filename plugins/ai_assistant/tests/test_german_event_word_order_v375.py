import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_subject_first_kinship_rescue():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Arthur befreit seinen Halbbruder Orm "
            "aus dem Gefängnis. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:orm" in keys
    assert "character:halbbruder orm" not in keys


def test_verb_first_kinship_rescue_after_clause():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Um herauszufinden, wo David sich versteckt, "
            "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis. "
            "Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:orm" in keys


def test_leading_location_battle():
    result = EventIntelligence().analyze(
        text=(
            "Handlung In Necrus kämpft Arthur gegen David, "
            "um seinen Sohn zu retten. Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    edge_types = {edge["edge_type"] for edge in result["edges"]}

    assert "character:arthur" in keys
    assert "character:david" in keys
    assert "location:necrus" in keys
    assert "occurs_at" in edge_types


def test_complete_real_world_bundle():
    result = EventIntelligence().analyze(
        text=(
            "Handlung "
            "Um herauszufinden, wo David sich versteckt, "
            "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis. "
            "Später erfahren sie, dass David Arthur Jr. entführt hat. "
            "In Necrus kämpft Arthur gegen David, "
            "um seinen Sohn zu retten. "
            "Produktion"
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}
    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert {
        "character:arthur",
        "character:orm",
        "character:david",
        "character:arthur jr",
        "location:necrus",
    } <= keys

    assert {"rescue", "kidnapping", "battle"} <= event_types
