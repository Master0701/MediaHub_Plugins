import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.decision_engine import DecisionEngine


def _ncis_analysis():
    return {
        "identification": {
            "title_candidate": "NCIS",
            "media_type": "unknown",
            "confidence": 0.40,
        },
        "online": {
            "executed": True,
            "ranking": {
                "decision": "probable_match",
                "confidence": 0.81,
                "best_match": {
                    "title": "NCIS",
                    "original_title": "NCIS",
                    "media_type": "series",
                    "provider_id": "tvdb",
                    "provider_name": "TheTVDB",
                    "score": 0.81,
                    "evidence_count": 3,
                    "penalties": [],
                },
            },
        },
        "episode_identity": {
            "status": "confirmed",
            "decision_authority": True,
            "series_title": "NCIS",
            "media_type": "series",
            "season": 8,
            "episode": 3,
            "episode_title": "Rache ist bitter",
            "confidence": 0.985,
            "confidence_percent": 98.5,
            "shared_concepts": [
                "marine",
                "killer",
                "sergeant",
            ],
            "matched_relationships": [
                ["marine", "killer"],
            ],
            "score_gap": 0.35,
        },
        "in_video": {
            "state": "completed",
            "completed_agents": 1,
            "agents": {},
        },
    }


def test_confirmed_episode_becomes_decision_evidence():
    result = DecisionEngine().evaluate(
        _ncis_analysis()
    )

    episode = next(
        item
        for item in result["all_evidence"]
        if item["source"] == "episode_identity"
    )

    assert episode["supports"] is True
    assert episode["confidence"] == 0.985

    assert (
        episode["value"]
        == "NCIS S08E03 – Rache ist bitter"
    )


def test_online_series_type_replaces_unknown_local_type():
    result = DecisionEngine().evaluate(
        _ncis_analysis()
    )

    assert result["media_type"] == "series"


def test_confirmed_episode_propagates_season_and_episode():
    result = DecisionEngine().evaluate(
        _ncis_analysis()
    )

    assert result["season"] == 8
    assert result["episodes"] == [3]


def test_online_plus_confirmed_episode_can_confirm_series():
    result = DecisionEngine().evaluate(
        _ncis_analysis()
    )

    assert result["status"] == "confirmed"
    assert result["title_candidate"] == "NCIS"
    assert result["media_type"] == "series"

    assert (
        result["independent_confirmations"]
        >= 2
    )

    sources = {
        item["source"]
        for item
        in result["confirmed_evidence"]
    }

    assert "online" in sources
    assert "episode_identity" in sources


def test_episode_without_decision_authority_does_not_confirm():
    analysis = _ncis_analysis()

    analysis["episode_identity"][
        "decision_authority"
    ] = False

    result = DecisionEngine().evaluate(
        analysis
    )

    sources = {
        item["source"]
        for item
        in result["confirmed_evidence"]
    }

    assert "episode_identity" not in sources
    assert result["status"] != "confirmed"


def test_unconfirmed_episode_does_not_confirm():
    analysis = _ncis_analysis()

    analysis["episode_identity"][
        "status"
    ] = "ambiguous"

    result = DecisionEngine().evaluate(
        analysis
    )

    sources = {
        item["source"]
        for item
        in result["confirmed_evidence"]
    }

    assert "episode_identity" not in sources
    assert result["status"] != "confirmed"


def test_compact_code_filename_is_not_identity_evidence():
    analysis = _ncis_analysis()

    analysis["identification"] = {
        "title_candidate": "6n76g68r",
        "media_type": "unknown",
        "confidence": 0.40,
    }

    result = DecisionEngine().evaluate(
        analysis
    )

    filename = next(
        item
        for item in result["all_evidence"]
        if item["source"] == "filename"
    )

    assert filename["supports"] is False
    assert filename["confidence"] == 0.0

    assert result["title_candidate"] == "NCIS"
    assert result["media_type"] == "series"
    assert result["season"] == 8
    assert result["episodes"] == [3]
    assert result["status"] == "confirmed"
