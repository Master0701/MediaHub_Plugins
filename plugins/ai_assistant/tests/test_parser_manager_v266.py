import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.parser_manager import ParserManager


def _source(url, source_type="custom_url"):
    return {
        "id": "source-1",
        "name": "Testquelle",
        "source_type": source_type,
        "url": url,
    }


def test_wikipedia_parser_is_selected():
    manager = ParserManager()
    result = manager.parse(
        source=_source("https://de.wikipedia.org/wiki/Aquaman"),
        scan_result={
            "url": "https://de.wikipedia.org/wiki/Aquaman",
            "title": "Aquaman – Wikipedia",
            "headings": ["Handlung", "Besetzung"],
            "text_preview": (
                "Aquaman ist ein US-amerikanischer Film aus dem Jahr 2018 "
                "und Teil des DC Extended Universe."
            ),
        },
    )

    assert result["selected_parser"] == "wikipedia"
    assert result["result"]["fields"]["title"] == "Aquaman"
    assert result["result"]["fields"]["metadata"]["universe"] == (
        "DC Extended Universe"
    )
    assert result["automatic_import"] is False


def test_generic_parser_is_fallback():
    manager = ParserManager()
    result = manager.parse(
        source=_source("https://example.com/media"),
        scan_result={
            "url": "https://example.com/media",
            "title": "Testfilm",
            "headings": ["Chronologie"],
            "text_preview": "Testfilm ist ein Film von 2024. Sequel.",
        },
    )

    assert result["selected_parser"] == "generic_html"
    assert result["result"]["fields"]["media_type"] == "movie"
    assert 2024 in result["result"]["fields"]["year_candidates"]


def test_parser_descriptors_are_available():
    manager = ParserManager()
    descriptors = manager.descriptors()
    ids = {item["parser_id"] for item in descriptors}

    assert {"wikipedia", "generic_html"} <= ids
    assert descriptors[0]["priority"] >= descriptors[-1]["priority"]
