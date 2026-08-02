from pathlib import Path


def test_knowledge_graph_validator_integrated_v702():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.knowledge_graph_validator "
        "import KnowledgeGraphValidator"
        in text
    )
    assert (
        "self.knowledge_graph_validator = "
        "KnowledgeGraphValidator()"
        in text
    )
    assert (
        "knowledge_graph_validation = "
        "self.knowledge_graph_validator.build("
        in text
    )
    assert (
        '"knowledge_graph_validation": '
        "knowledge_graph_validation"
        in text
    )
    assert (
        'context.document["knowledge_graph_validation"] = '
        "knowledge_graph_validation"
        in text
    )
