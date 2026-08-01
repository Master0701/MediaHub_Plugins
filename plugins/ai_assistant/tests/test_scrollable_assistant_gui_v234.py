from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_graph_and_analysis_tabs_are_scrollable():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "QScrollArea" in text
    assert "graph_scroll.setWidget(graph_page)" in text
    assert 'tabs.addTab(graph_scroll, "Knowledge Graph")' in text
    assert "analysis_scroll.setWidget(analysis_page)" in text
    assert 'tabs.addTab(analysis_scroll, "Dateianalyse & Lernen")' in text


def test_scrollbars_are_automatic():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert text.count(
        "Qt.ScrollBarPolicy.ScrollBarAsNeeded"
    ) >= 4
    assert "setWidgetResizable(True)" in text
