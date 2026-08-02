from pathlib import Path


def test_plugin_integrates_reasoning_intelligence_v510():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert "from services.reasoning_intelligence import ReasoningIntelligence" in text
    assert "self.reasoning_intelligence = ReasoningIntelligence()" in text
    assert "reasoning_intelligence = self.reasoning_intelligence.analyze" in text
    assert '"reasoning_intelligence": reasoning_intelligence' in text
    assert 'context.document["reasoning_intelligence"] = reasoning_intelligence' in text
