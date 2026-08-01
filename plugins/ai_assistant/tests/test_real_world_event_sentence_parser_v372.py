import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence

SOURCE = {"id": "wiki"}


def test_real_aquaman_plot_forms():
    text = (
        "Handlung "
        "Um herauszufinden, wo David sich versteckt, befreit Arthur "
        "seinen Halbbruder Orm aus dem Gefängnis. "
        "Später erfahren sie, dass David Arthur Jr. entführt hat. "
        "In Necrus kämpft Arthur gegen David, um seinen Sohn zu retten. "
        "Produktion"
    )
    result = EventIntelligence().analyze(text=text, source=SOURCE)

    keys = {node["key"] for node in result["nodes"]}
    event_types = {
        node["metadata"]["event_type"]
        for node in result["nodes"]
        if node["node_type"] == "event"
    }

    assert "character:arthur" in keys
    assert "character:orm" in keys
    assert "character:david" in keys
    assert "character:arthur jr" in keys
    assert "location:necrus" in keys
    assert {"rescue", "kidnapping", "battle"} <= event_types


def test_no_cross_sentence_garbage_nodes():
    text = (
        "Handlung "
        "Der Geist von Kordax geht zu Orm, der gegen Arthur kämpft. "
        "Nachdem sein Halbbruder wieder von Kordax' Geist befreit ist, "
        "wirft Arthur den Dreizack. "
        "Produktion"
    )
    result = EventIntelligence().analyze(text=text, source=SOURCE)
    keys = {node["key"] for node in result["nodes"]}

    assert not any("nachdem" in key for key in keys)
    assert "character:ist" not in keys
    assert not any("zu befreien" in key for key in keys)


def test_plot_section_only():
    text = (
        "Handlung Arthur kämpft gegen David. "
        "Produktion James Wan kämpfte gegen Zeitdruck."
    )
    result = EventIntelligence().analyze(text=text, source=SOURCE)
    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:david" in keys
    assert "character:james wan" not in keys
