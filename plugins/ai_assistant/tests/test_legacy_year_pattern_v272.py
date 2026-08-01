import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_extractor import KnowledgeExtractor


def test_year_before_erschien_is_recognized():
    result = KnowledgeExtractor().extract(
        source={
            "id": "wiki",
            "name": "Wikipedia",
            "url": "https://de.wikipedia.org/wiki/Aquaman",
        },
        parser_result={
            "result": {
                "parser_id": "wikipedia",
                "confidence": 0.82,
                "fields": {
                    "title": "Aquaman",
                    "media_type": "movie",
                    "year_candidates": [1941, 2018, 2019],
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
