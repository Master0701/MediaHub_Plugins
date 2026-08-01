import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_extractor import KnowledgeExtractor
from services.semantic_knowledge_engine import SemanticKnowledgeEngine


SOURCE = {
    "id": "wiki",
    "name": "Wikipedia",
    "url": "https://de.wikipedia.org/wiki/Aquaman",
}


def test_legacy_extractor_call_still_selects_2018():
    result = KnowledgeExtractor().extract(
        source=SOURCE,
        parser_result={
            "result": {
                "parser_id": "wikipedia",
                "confidence": 0.82,
                "fields": {
                    "title": "Aquaman",
                    "media_type": "movie",
                    "year_candidates": [1941, 2018, 2019],
                    "metadata": {
                        "universe": "DC Extended Universe",
                    },
                },
            }
        },
        scan_result={
            "text_preview": (
                "Im Dezember 2018 erschien der Film Aquaman, "
                "der erste eigenständige Kinofilm."
            )
        },
    )

    assert result["entity_proposals"][0]["year"] == 2018


def test_semantic_engine_recognizes_erschien_der_film():
    result = SemanticKnowledgeEngine().analyze(
        title="Aquaman",
        text=(
            "In Justice League aus dem Jahr 2017 hat Aquaman "
            "einen Auftritt. Im Dezember 2018 erschien der Film Aquaman."
        ),
        source=SOURCE,
    )

    movies = [
        item
        for item in result["entity_proposals"]
        if item["entity_type"] == "movie"
    ]
    assert any(item["year"] == 2018 for item in movies)
    assert not any(item["year"] == 2017 for item in movies)
