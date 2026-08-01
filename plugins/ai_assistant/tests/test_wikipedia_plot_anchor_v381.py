import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.event_intelligence import EventIntelligence


SOURCE = {"id": "wiki"}


def test_toc_headings_are_ignored():
    text = (
        "Inhaltsverzeichnis 1 Handlung 2 Produktion 3 Synchronisation "
        "Aquaman: Lost Kingdom ist ein Film. "
        "Handlung [ Bearbeiten | Quelltext bearbeiten ] "
        "Arthur befreit seinen Halbbruder Orm aus dem Gefängnis. "
        "Später erfahren sie, dass David Arthur Jr. entführt hat. "
        "In Necrus kämpft Arthur gegen David, um seinen Sohn zu retten. "
        "Produktion [ Bearbeiten | Quelltext bearbeiten ] "
        "Die Dreharbeiten fanden in London statt."
    )

    plot = EventIntelligence._extract_plot_text(text)

    assert "Arthur befreit" in plot
    assert "In Necrus kämpft Arthur" in plot
    assert "Die Dreharbeiten" not in plot
    assert not plot.startswith("2 Produktion")


def test_real_wikipedia_style_produces_events():
    text = (
        "Inhaltsverzeichnis Handlung Produktion Synchronisation "
        "Handlung [ Bearbeiten | Quelltext bearbeiten ] "
        "Um herauszufinden, wo David sich versteckt, "
        "befreit Arthur seinen Halbbruder Orm aus dem Gefängnis. "
        "Später erfahren sie, dass David Arthur Jr. entführt hat. "
        "In Necrus kämpft Arthur gegen David, "
        "um seinen Sohn zu retten. "
        "Produktion [ Bearbeiten | Quelltext bearbeiten ] "
        "James Wan führte Regie."
    )

    result = EventIntelligence().analyze(
        text=text,
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
    assert result["event_count"] >= 3


def test_plain_source_fallback_still_works():
    text = (
        "Handlung "
        "Arthur kämpft gegen David. "
        "Weitere Handlung mit genügend Text für einen plausiblen Abschnitt. "
        "Dieser Teil beschreibt das Geschehen ausführlich und vollständig. "
        "Produktion "
        "Die Produktion begann später."
    )

    plot = EventIntelligence._extract_plot_text(text)

    assert "Arthur kämpft gegen David" in plot
    assert "Die Produktion begann" not in plot
