import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.entity_proposal_quality_filter import (
    EntityProposalQualityFilter,
)


def build(proposals):
    return EntityProposalQualityFilter.build(
        missing_entity_resolution={
            "missing_node_proposals": proposals
        }
    )


def test_accepts_clean_character_name():
    result = build([{
        "node_key": "character:arthur curry",
        "node_type": "character",
        "title": "Arthur Curry",
    }])

    assert result["summary"]["accepted_proposal_count"] == 1
    assert result["summary"]["rejected_proposal_count"] == 0


def test_rejects_sentence_fragment_character():
    result = build([{
        "node_key": "character:um atlantische artefakte zu finden. er",
        "node_type": "character",
        "title": "Um Atlantische Artefakte Zu Finden. Er",
    }])

    assert result["summary"]["accepted_proposal_count"] == 0
    assert result["summary"]["rejected_proposal_count"] == 1


def test_rejects_action_phrase_character():
    result = build([{
        "node_key": "character:befreit arthur",
        "node_type": "character",
        "title": "Befreit Arthur",
    }])

    rejected = result["rejected_proposals"][0]
    assert "starts_with_verb" in rejected["quality_reasons"]


def test_keeps_artifact_proposal_for_review():
    result = build([{
        "node_key": "artifact:schwarzer dreizack",
        "node_type": "artifact",
        "title": "Schwarzer Dreizack",
    }])

    assert result["summary"]["accepted_proposal_count"] == 1
    assert result["automatic_import"] is False
