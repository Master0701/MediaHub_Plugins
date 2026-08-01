import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.timeline_order_intelligence import (
    TimelineOrderIntelligence,
)


MAIN = {
    "key": "movie:aquaman: lost kingdom:2023",
    "node_type": "movie",
    "title": "Aquaman: Lost Kingdom",
    "year": 2023,
}
SOURCE = {"id": "wikipedia-test"}


def analyze(text):
    return TimelineOrderIntelligence.analyze(
        main_node=MAIN,
        text=text,
        source=SOURCE,
        franchise_collection={
            "franchise_name": "Aquaman",
        },
        franchise_relations={},
    )


def node_keys(result):
    return {
        node["key"]
        for node in result["nodes"]
    }


def test_multiword_predecessor_title_is_preserved():
    result = analyze(
        "Chronologie ← Blue Beetle "
        "Aquaman: Lost Kingdom ist ein Film."
    )

    assert "movie:blue beetle" in node_keys(result)
    assert "movie:blue" not in node_keys(result)


def test_three_word_predecessor_title_is_preserved():
    result = analyze(
        "Chronologie ← The Dark Knight "
        "Aquaman: Lost Kingdom ist ein Film."
    )

    assert "movie:the dark knight" in node_keys(result)


def test_plain_chronology_title_still_works():
    result = analyze(
        "Chronologie ← Blue Beetle"
    )

    assert "movie:blue beetle" in node_keys(result)


def test_strategy_v452():
    result = analyze(
        "Chronologie ← Blue Beetle"
    )

    assert result["strategy"] == (
        "timeline_order_intelligence_v452"
    )
