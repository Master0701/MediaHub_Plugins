from pathlib import Path


def test_franchise_knowledge_graph_integrated_v590():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.franchise_knowledge_graph "
        "import FranchiseKnowledgeGraph"
        in text
    )
    assert (
        "self.franchise_knowledge_graph = FranchiseKnowledgeGraph()"
        in text
    )
    assert (
        "franchise_knowledge_graph = "
        "self.franchise_knowledge_graph.build("
        in text
    )
    assert (
        '"franchise_knowledge_graph": franchise_knowledge_graph'
        in text
    )
    assert (
        'context.document["franchise_knowledge_graph"] = '
        "franchise_knowledge_graph"
        in text
    )
