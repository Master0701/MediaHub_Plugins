from pathlib import Path


def test_missing_entity_resolver_integrated_v703():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.missing_entity_resolver "
        "import MissingEntityResolver"
        in text
    )
    assert (
        "self.missing_entity_resolver = "
        "MissingEntityResolver()"
        in text
    )
    assert (
        "missing_entity_resolution = "
        "self.missing_entity_resolver.build("
        in text
    )
    assert (
        '"missing_entity_resolution": '
        "missing_entity_resolution"
        in text
    )
    assert (
        'context.document["missing_entity_resolution"] = '
        "missing_entity_resolution"
        in text
    )
