import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def text():
    return PLUGIN_PATH.read_text(encoding="utf-8")


def test_plugin_syntax_and_version():
    source = text()

    ast.parse(source)
    assert 'VERSION = "' in source


def test_service_import_and_initialization():
    source = text()

    assert (
        "from services.timeline_order_intelligence "
        "import TimelineOrderIntelligence"
        in source
    )
    assert (
        "self.timeline_order_intelligence = "
        "TimelineOrderIntelligence()"
        in source
    )


def test_full_scan_integration():
    source = text()

    assert (
        "timeline_order_intelligence = ("
        in source
    )
    assert (
        "timeline_order_intelligence,"
        in source
    )
    assert (
        'context.document["timeline_order_intelligence"]'
        in source
    )
    assert (
        '"timeline_order_intelligence": '
        "timeline_order_intelligence"
        in source
    )


def test_graph_builder_receives_timeline_nodes_and_edges():
    source = text()

    assert (
        'timeline_order_intelligence.get("nodes")'
        in source
    )
    assert (
        'timeline_order_intelligence.get("edges")'
        in source
    )
