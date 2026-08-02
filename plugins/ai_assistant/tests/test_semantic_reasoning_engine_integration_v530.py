from pathlib import Path


def test_plugin_integrates_semantic_reasoning_engine_v530():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.semantic_reasoning_engine "
        "import SemanticReasoningEngine"
        in text
    )
    assert (
        "self.semantic_reasoning_engine = SemanticReasoningEngine()"
        in text
    )
    assert (
        "semantic_reasoning = self.semantic_reasoning_engine.analyze("
        in text
    )
    assert '"semantic_reasoning": semantic_reasoning' in text
    assert (
        'context.document["semantic_reasoning"] = semantic_reasoning'
        in text
    )
