from pathlib import Path


def test_global_knowledge_fusion_integrated_v690():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.global_knowledge_fusion "
        "import GlobalKnowledgeFusion"
        in text
    )
    assert (
        "self.global_knowledge_fusion = "
        "GlobalKnowledgeFusion()"
        in text
    )
    assert (
        "global_knowledge = "
        "self.global_knowledge_fusion.build("
        in text
    )
    assert '"global_knowledge": global_knowledge' in text
    assert (
        'context.document["global_knowledge"] = '
        "global_knowledge"
        in text
    )
