from pathlib import Path


def test_canonical_conflict_resolver_integrated_v660():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.canonical_conflict_resolver "
        "import CanonicalConflictResolver"
        in text
    )
    assert (
        "self.canonical_conflict_resolver = "
        "CanonicalConflictResolver()"
        in text
    )
    assert (
        "canonical_conflicts = "
        "self.canonical_conflict_resolver.build("
        in text
    )
    assert '"canonical_conflicts": canonical_conflicts' in text
    assert (
        'context.document["canonical_conflicts"] = '
        "canonical_conflicts"
        in text
    )
