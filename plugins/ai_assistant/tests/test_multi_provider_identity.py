import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.decision_engine import DecisionEngine


def test_multi_provider_exact_single_word_title_is_confirmation():
    analysis = {
        "identification": {
            "title_candidate": "Chappie",
            "media_type": "movie",
            "confidence": 0.40,
        },
        "online": {
            "provider_results": [
                {
                    "provider_id": "tmdb",
                    "provider_name": "TMDb",
                    "matches": [
                        {
                            "title": "Chappie",
                            "year": 2015,
                            "media_type": "movie",
                            "provider_confidence": 0.6792,
                        }
                    ],
                },
                {
                    "provider_id": "tvdb",
                    "provider_name": "TheTVDB",
                    "matches": [
                        {
                            "title": "Chappie",
                            "year": 2015,
                            "media_type": "movie",
                            "provider_confidence": 0.90,
                        }
                    ],
                },
            ],
            "ranking": {
                "decision": "ambiguous",
                "best_match": {
                    "title": "Chappie",
                    "provider_name": "TheTVDB",
                    "score": 0.323,
                    "evidence_count": 3,
                    "penalties": [
                        "weak_single_word_variant",
                    ],
                },
            },
        },
        "in_video": {
            "state": "completed",
            "agents": {},
        },
    }

    result = DecisionEngine().evaluate(analysis)

    online = next(
        item
        for item in result["all_evidence"]
        if item["source"] == "online"
    )

    assert online["supports"] is True
    assert online["confidence"] > 0.70

    assert (
        "Mehrere unabhängige Online-Provider"
        in online["detail"]
    )

    assert result["independent_confirmations"] == 2
    assert result["confidence"] >= 0.62
    assert result["status"] != "insufficient"


def test_single_provider_weak_single_word_stays_blocked():
    analysis = {
        "identification": {
            "title_candidate": "Aqua",
            "media_type": "unknown",
            "confidence": 0.40,
        },
        "online": {
            "provider_results": [
                {
                    "provider_id": "wikipedia",
                    "provider_name": "Wikipedia",
                    "matches": [
                        {
                            "title": "Aqua",
                            "media_type": "movie",
                            "provider_confidence": 0.72,
                        }
                    ],
                }
            ],
            "ranking": {
                "decision": "ambiguous",
                "best_match": {
                    "title": "Aqua",
                    "provider_name": "Wikipedia",
                    "score": 0.2927,
                    "evidence_count": 3,
                    "penalties": [
                        "weak_single_word_variant",
                    ],
                },
            },
        },
        "in_video": {
            "state": "completed",
            "agents": {},
        },
    }

    result = DecisionEngine().evaluate(analysis)

    online = next(
        item
        for item in result["all_evidence"]
        if item["source"] == "online"
    )

    assert online["supports"] is False


def test_official_alias_confirms_same_media_identity():
    analysis = {
        "identification": {
            "title_candidate": "Live Die Repeat",
            "media_type": "movie",
            "confidence": 0.40,
        },
        "online": {
            "provider_results": [
                {
                    "provider_id": "tmdb",
                    "provider_name": "TMDb",
                    "matches": [
                        {
                            "title": "Edge of Tomorrow",
                            "original_title": "Edge of Tomorrow",
                            "aliases": [
                                "Live Die Repeat",
                            ],
                            "year": 2014,
                            "media_type": "movie",
                            "provider_confidence": 0.76,
                        }
                    ],
                }
            ],
            "ranking": {
                "decision": "strong_match",
                "best_match": {
                    "title": "Edge of Tomorrow",
                    "original_title": "Edge of Tomorrow",
                    "aliases": [
                        "Live Die Repeat",
                    ],
                    "score": 0.8875,
                    "evidence_count": 4,
                    "penalties": [],
                },
            },
        },
        "in_video": {
            "state": "completed",
            "agents": {},
        },
    }

    result = DecisionEngine().evaluate(analysis)

    online = next(
        item
        for item in result["all_evidence"]
        if item["source"] == "online"
    )

    assert online["supports"] is True
    assert online["confidence"] >= 0.85

    assert (
        "offiziellen Alternativtitel"
        in online["detail"]
    )

    assert result["confidence"] >= 0.62
    assert result["status"] != "insufficient"
