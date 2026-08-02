from pathlib import Path


def test_plugin_integrates_temporal_causal_intelligence_v540():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.temporal_causal_intelligence "
        "import TemporalCausalIntelligence"
        in text
    )
    assert (
        "self.temporal_causal_intelligence = "
        "TemporalCausalIntelligence()"
        in text
    )
    assert (
        "temporal_causal_intelligence = "
        "self.temporal_causal_intelligence.analyze("
        in text
    )
    assert (
        '"temporal_causal_intelligence": '
        "temporal_causal_intelligence"
        in text
    )
    assert (
        'context.document["temporal_causal_intelligence"] = '
        "temporal_causal_intelligence"
        in text
    )
