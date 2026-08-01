import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plot_cleaner import PlotCleaner
from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_plot_cleaner_removes_headings_and_edit_markers():
    cleaned = PlotCleaner.clean(
        "Handlung [ Bearbeiten | Quelltext bearbeiten ] "
        "Arthur kämpft gegen David. "
        "Produktion [ Bearbeiten | Quelltext bearbeiten ] "
        "James Wan führte Regie."
    )

    assert cleaned == "Arthur kämpft gegen David."


def test_plain_short_section_is_extracted_and_cleaned():
    result = EventIntelligence().analyze(
        text=(
            "Handlung Arthur kämpft gegen David. "
            "Produktion James Wan kämpfte gegen Zeitdruck."
        ),
        source=SOURCE,
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "character:arthur" in keys
    assert "character:david" in keys
    assert "character:handlung arthur" not in keys
    assert "character:produktion james wan" not in keys
    assert "character:zeitdruck" not in keys


def test_subject_first_rescue_has_clean_actor():
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
    assert "character:handlung arthur" not in keys


def test_wikipedia_style_bundle_still_works():
    result = EventIntelligence().analyze(
        text=(
            "Inhaltsverzeichnis 1 Handlung 2 Produktion "
            "Handlung [ Bearbeiten | Quelltext bearbeiten ] "
            "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis. "
            "Später erfahren sie, dass David Arthur Jr. entführt hat. "
            "In Necrus kämpft Arthur gegen David, "
            "um seinen Sohn zu retten. "
            "Produktion [ Bearbeiten | Quelltext bearbeiten ] "
            "James Wan führte Regie."
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
    assert not any("produktion" in key for key in keys)
