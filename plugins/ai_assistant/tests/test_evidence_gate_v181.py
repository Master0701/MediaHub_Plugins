from pathlib import Path
import sys

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.decision_engine import DecisionEngine
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.agents.supervisor_agent import SupervisorAgent


def _analysis_with_weak_aqua_match():
    return {
        "identification": {
            "title_candidate": "pso aqua2 ts",
            "media_type": "unknown",
            "confidence": 0.4,
            "requires_external_lookup": True,
        },
        "online": {
            "executed": True,
            "ranking": {
                "decision": "ambiguous",
                "confidence": 0.2927,
                "best_match": {
                    "title": "Aqua",
                    "provider_name": "Wikipedia",
                    "score": 0.2927,
                    "evidence_count": 3,
                    "penalties": ["weak_single_word_variant"],
                },
            },
        },
        "in_video": {"state": "completed", "completed_agents": 0, "agents": {}},
    }


def test_weak_wikipedia_match_is_not_confirmation():
    result = DecisionEngine().evaluate(_analysis_with_weak_aqua_match())
    online = next(item for item in result["all_evidence"] if item["source"] == "online")
    assert online["supports"] is False
    assert "nicht als Identitätsbestätigung" in online["detail"]
    assert result["independent_confirmations"] == 1
    assert not any("Wikipedia bestätigt" in item for item in result["explanation"]["why"])


def test_supervisor_does_not_use_ambiguous_online_score_as_confirmation():
    analysis = _analysis_with_weak_aqua_match()
    analysis["decision"] = DecisionEngine().evaluate(analysis)
    result = SupervisorAgent().evaluate(analysis)
    assert result["online_confidence"] == 0.2927
    assert result["effective_online_confidence"] == 0.0
    assert result["online_identity_confirmed"] is False
    assert result["combined_confidence"] == 0.4


def test_probable_online_match_can_confirm_identity():
    analysis = _analysis_with_weak_aqua_match()
    analysis["online"]["ranking"] = {
        "decision": "probable_match",
        "confidence": 0.82,
        "best_match": {
            "title": "pso aqua2 ts",
            "provider_name": "TVDB",
            "score": 0.82,
            "evidence_count": 3,
            "penalties": [],
        },
    }
    result = DecisionEngine().evaluate(analysis)
    online = next(item for item in result["all_evidence"] if item["source"] == "online")
    assert online["supports"] is True

def test_supervisor_requires_in_video_for_weak_local_identity_with_single_online_evidence():
    from services.agents.supervisor_agent import SupervisorAgent

    analysis = {
        "identification": {
            "title_candidate": "Pso-aqua2-ts-1080p",
            "confidence": 0.23,
            "requires_external_lookup": True,
        },
        "online": {
            "executed": True,
            "ranking": {
                "decision": "probable_match",
                "confidence": 0.84,
                "best_match": {
                    "title": "Aquaman and the Lost Kingdom",
                    "score": 0.84,
                    "evidence_count": 1,
                },
            },
        },
        "in_video": {
            "state": "deferred",
        },
    }

    result = SupervisorAgent().evaluate(analysis)

    in_video_step = next(
        step
        for step in result["next_steps"]
        if step["agent"] == "in_video"
    )

    assert in_video_step["required"] is True
    assert in_video_step["state"] == "pending"


def test_supervisor_can_defer_in_video_when_online_identity_has_multiple_evidence():
    from services.agents.supervisor_agent import SupervisorAgent

    analysis = {
        "identification": {
            "title_candidate": "Chappie",
            "confidence": 0.40,
            "requires_external_lookup": True,
        },
        "online": {
            "executed": True,
            "ranking": {
                "decision": "strong_match",
                "confidence": 0.82,
                "best_match": {
                    "title": "Chappie",
                    "score": 0.82,
                    "evidence_count": 3,
                },
            },
        },
        "in_video": {
            "state": "deferred",
        },
    }

    result = SupervisorAgent().evaluate(analysis)

    in_video_step = next(
        step
        for step in result["next_steps"]
        if step["agent"] == "in_video"
    )

    assert in_video_step["required"] is False
    assert in_video_step["state"] == "deferred"

