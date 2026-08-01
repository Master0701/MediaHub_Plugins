import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_extractor import KnowledgeExtractor


SOURCE = {
    "id": "wiki",
    "name": "Wikipedia",
    "url": "https://de.wikipedia.org/wiki/Aquaman",
}


def parser_result():
    return {
        "result": {
            "parser_id": "wikipedia",
            "confidence": 0.82,
            "fields": {
                "title": "Aquaman",
                "media_type": "movie",
                "year_candidates": [1941, 1967, 2017, 2018],
                "metadata": {"universe": "DC Extended Universe"},
            },
        }
    }


def semantic_result():
    return {
        "primary_entity_type": "character",
        "primary_entity_confidence": 0.90,
        "entity_proposals": [
            {
                "title": "Aquaman",
                "entity_type": "movie",
                "year": 2018,
                "confidence": 0.89,
                "sentence": "Im Dezember 2018 erschien der Film Aquaman.",
                "reason": "Titel, Typ und Jahr stehen im selben Satz.",
            },
            {
                "title": "Aquaman",
                "entity_type": "series",
                "year": 1967,
                "confidence": 0.89,
                "sentence": "1967 erschien die Zeichentrickserie Aquaman.",
                "reason": "Titel, Typ und Jahr stehen im selben Satz.",
            },
        ],
    }


def extracted():
    return KnowledgeExtractor().extract(
        source=SOURCE,
        parser_result=parser_result(),
        scan_result={},
        semantic_result=semantic_result(),
    )


def test_character_has_no_wrong_year():
    character = next(
        item for item in extracted()["entity_proposals"]
        if item["media_type"] == "character"
    )
    assert character["year"] is None


def test_movie_and_series_are_separate():
    keys = {
        (item["media_type"], item["year"])
        for item in extracted()["entity_proposals"]
    }
    assert ("character", None) in keys
    assert ("movie", 2018) in keys
    assert ("series", 1967) in keys


def test_no_entity_has_2017():
    assert all(
        item.get("year") != 2017
        for item in extracted()["entity_proposals"]
    )
