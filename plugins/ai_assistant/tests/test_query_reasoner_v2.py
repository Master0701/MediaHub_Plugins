import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.search_variant_reasoner import SearchVariantReasoner
from services.online_result_ranker import OnlineResultRanker

def test_cleanup_and_compound_split():
    result=SearchVariantReasoner().build({"identification":{"title_candidate":"NCISLA.S01E02.1080p.WEB-DL-GROUP","media_type":"series"},"file":{}})
    titles=[x["title"] for x in result["variants"]]
    assert any("NCIS LA" in x for x in titles)
    assert not any("1080p" in x for x in titles)

def test_weak_single_word_false_positive():
    query={"title":"PSO","media_type":"series","search_variants":[]}
    providers=[{"provider_id":"wikipedia","provider_name":"Wikipedia","trust":.6,"priority":50,"matches":[{"title":"Aquädukt","media_type":"article","search_variant":"PSO","search_variant_score":.3}]}]
    result=OnlineResultRanker().rank(query,providers)
    assert result["decision"] == "ambiguous"
    assert result["best_match"]["score"] < .35

def test_exact_alias_plus_type_is_probable():
    query={"title":"SGA","media_type":"series"}
    providers=[{"provider_id":"tvdb","provider_name":"TVDB","trust":.95,"priority":90,"matches":[{"title":"Stargate Atlantis","aliases":["SGA"],"media_type":"series","search_variant":"SGA","search_variant_score":.98}]}]
    result=OnlineResultRanker().rank(query,providers)
    assert result["best_match"]["evidence_count"] >= 2
    assert result["decision"] in {"probable_match","strong_match"}

def test_query_reasoner_keeps_filename_primary_over_ocr():
    reasoner = SearchVariantReasoner()

    analysis = {
        "identification": {
            "title_candidate": "Chappie - Kopie",
            "media_type": "movie",
        },
        "file": {
            "name": "Chappie - Kopie.mp4",
        },
        "in_video": {
            "agents": {
                "ocr_agent": {
                    "findings": [
                        {"text": "18 MONTHS EARLIER"},
                        {"text": "3 DAYS LATER"},
                        {"text": "PRESENT DAY"},
                        {"text": "STAR TREK"},
                    ]
                }
            }
        },
    }

    result = reasoner.build(analysis)

    titles = {
        item["title"].casefold()
        for item in result["variants"]
    }

    assert result["primary_title"] == "Chappie"

    assert "chappie" in titles
    assert "star trek" in titles

    assert "chappie kopie" not in titles
    assert "18 months earlier" not in titles
    assert "3 days later" not in titles
    assert "present day" not in titles


def test_query_reasoner_removes_copy_suffixes():
    reasoner = SearchVariantReasoner()

    samples = (
        "Chappie - Kopie.mp4",
        "Chappie - Copy.mp4",
        "Chappie - Kopie (2).mp4",
        "Chappie - Copy (2).mp4",
    )

    for value in samples:
        assert reasoner._clean_title(value) == "Chappie"

