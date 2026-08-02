from pathlib import Path


def test_cross_franchise_resolver_integrated_v670():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.cross_franchise_resolver "
        "import CrossFranchiseResolver"
        in text
    )
    assert (
        "self.cross_franchise_resolver = "
        "CrossFranchiseResolver()"
        in text
    )
    assert (
        "cross_franchise = "
        "self.cross_franchise_resolver.build("
        in text
    )
    assert '"cross_franchise": cross_franchise' in text
    assert (
        'context.document["cross_franchise"] = '
        "cross_franchise"
        in text
    )
