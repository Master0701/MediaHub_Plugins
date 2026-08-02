from pathlib import Path


def test_entity_resolution_graph_integrated_v610():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.entity_resolution_graph "
        "import EntityResolutionGraph"
        in text
    )
    assert (
        "self.entity_resolution_graph = EntityResolutionGraph()"
        in text
    )
    assert (
        "entity_resolution_graph = "
        "self.entity_resolution_graph.build("
        in text
    )
    assert '"entity_resolution_graph": entity_resolution_graph' in text
    assert (
        'context.document["entity_resolution_graph"] = '
        "entity_resolution_graph"
        in text
    )
