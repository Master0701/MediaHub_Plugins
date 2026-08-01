import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_extractor import KnowledgeExtractor


def _source():
    return {
        "id": "wiki",
        "name": "Wikipedia",
        "url": "https://de.wikipedia.org/wiki/Aquaman",
        "trust": 0.84,
    }


def test_entity_and_universe_proposals_are_created():
    parser_result = {
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
    }
    scan_result = {
        "text_preview": (
            "Im Dezember 2018 erschien der Film Aquaman, "
            "der erste eigenständige Kinofilm."
        )
    }

    result = KnowledgeExtractor().extract(
        source=_source(),
        parser_result=parser_result,
        scan_result=scan_result,
    )

    assert result["entity_proposals"][0]["title"] == "Aquaman"
    assert result["entity_proposals"][0]["year"] == 2018
    assert result["group_proposals"][0]["group_type"] == "universe"
    assert result["automatic_import"] is False


def test_ambiguous_years_are_not_selected_blindly():
    parser_result = {
        "result": {
            "parser_id": "generic_html",
            "confidence": 0.58,
            "fields": {
                "title": "Test",
                "year_candidates": [1941, 1962, 2018],
            },
        }
    }

    result = KnowledgeExtractor().extract(
        source=_source(),
        parser_result=parser_result,
        scan_result={"text_preview": "Mehrere historische Jahreszahlen."},
    )

    assert result["entity_proposals"][0]["year"] is None
    assert any(
        item["field"] == "year_candidates"
        for item in result["field_candidates"]
    )
    assert result["warnings"]


def test_possible_sequel_creates_relation_proposal():
    parser_result = {
        "result": {
            "parser_id": "wikipedia",
            "confidence": 0.82,
            "fields": {
                "title": "Aquaman",
                "metadata": {
                    "possible_sequel_title": (
                        "Aquaman and the Lost Kingdom"
                    ),
                },
            },
        }
    }

    result = KnowledgeExtractor().extract(
        source=_source(),
        parser_result=parser_result,
    )

    proposal = result["relation_proposals"][0]
    assert proposal["relation_type"] == "sequel"
    assert proposal["target_title"] == "Aquaman and the Lost Kingdom"
    assert proposal["requires_confirmation"] is True
