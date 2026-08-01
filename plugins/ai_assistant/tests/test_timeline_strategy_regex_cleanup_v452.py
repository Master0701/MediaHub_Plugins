from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tests" / "test_timeline_order_intelligence_bundle_v450.py"


def test_old_v451_strategy_assertion_is_removed():
    text = TARGET.read_text(encoding="utf-8")

    assert '"timeline_order_intelligence_v451"' not in text
    assert 'startswith(' in text
    assert '"timeline_order_intelligence_v"' in text
