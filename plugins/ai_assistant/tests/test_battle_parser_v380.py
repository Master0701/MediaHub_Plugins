import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_parser import BattleParser
from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_direct_battle_sentence():
    result = BattleParser.parse(
        "Arthur kämpft gegen David."
    )

    assert result[0]["actor"] == "Arthur"
    assert result[0]["opponent"] == "David"
    assert result[0]["location"] is None


def test_inverted_battle_sentence_with_location():
    result = BattleParser.parse(
        "In Necrus kämpft Arthur gegen David, "
        "um seinen Sohn zu retten."
    )

    assert result[0]["actor"] == "Arthur"
    assert result[0]["opponent"] == "David"
    assert result[0]["location"] == "Necrus"


def test_auf_der_location_sentence():
    result = BattleParser.parse(
        "Auf der Vulkaninsel kämpfte Arthur gegen Orm."
    )

    assert result[0]["actor"] == "Arthur"
    assert result[0]["opponent"] == "Orm"
    assert result[0]["location"] == "Vulkaninsel"


def test_waehrend_context_sentence():
    result = BattleParser.parse(
        "Während der Schlacht kämpfte Thor gegen Hela."
    )

    assert result[0]["actor"] == "Thor"
    assert result[0]["opponent"] == "Hela"
    assert result[0]["context"] == "Schlacht"


def test_event_intelligence_creates_battle_and_location():
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

    events = [
        node
        for node in result["nodes"]
        if node["node_type"] == "event"
    ]
    assert events[0]["metadata"]["event_type"] == "battle"
    assert events[0]["metadata"]["parser"] == "battle_parser_v380"


def test_complete_aquaman_bundle():
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
