import sys
from pathlib import Path


AI_ROOT = Path(__file__).resolve().parents[1]

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from services.search_variant_reasoner import SearchVariantReasoner


def test_structured_identity_hint_is_primary_search_variant():
    reasoner = SearchVariantReasoner()

    result = reasoner.build(
        {
            "identification": {
                "media_type": "movie",
                "title_candidate": "12 Monkeys",
                "identity_hint_title": "12 Monkeys",
                "identity_hint_year": 1995,
                "identity_hint_applied": True,
                "normalized_name": (
                    "12 Monkeys microHD Raistlin911"
                ),
            },
            "file": {
                "name": (
                    "12.Monkeys.1995.GERMAN.1040p."
                    "microHD.x264-Raistlin911.mkv"
                ),
            },
        }
    )

    assert result["variants"]

    first = result["variants"][0]

    assert first["title"] == "12 Monkeys"
    assert first["source"] == "identity_hint"

    assert result["primary_title"] == "12 Monkeys"

    rejected_hint = [
        item
        for item in result["quality_gate"]["rejected"]
        if (
            item.get("title") == "12 Monkeys"
            and item.get("source") == "identity_hint"
        )
    ]

    assert rejected_hint == []
