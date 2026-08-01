from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INTEGRATION = (
    ROOT
    / "tests"
    / "test_timeline_order_integration_v450.py"
)
BUNDLE = (
    ROOT
    / "tests"
    / "test_timeline_order_intelligence_bundle_v450.py"
)


def test_no_obsolete_fixed_plugin_version_remains():
    text = INTEGRATION.read_text(encoding="utf-8")

    assert 'VERSION = "4.5.0"' not in text
    assert 'VERSION = "' in text


def test_no_obsolete_fixed_strategy_version_remains():
    text = BUNDLE.read_text(encoding="utf-8")

    assert (
        '"timeline_order_intelligence_v451"'
        not in text
    )
    assert (
        '"timeline_order_intelligence_v"'
        in text
    )
