import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.reasoner_learning import ReasonerLearningStore


def _proposal():
    return {
        "id": "proposal-1",
        "kind": "direct_relation",
        "relation_type": "spin_off",
        "confidence": 0.80,
        "evidence": [
            {"type": "spin_off_metadata", "weight": 0.96},
        ],
    }


def test_accepted_decisions_can_raise_confidence(tmp_path):
    store = ReasonerLearningStore(tmp_path / "knowledge.sqlite3")
    store.record(_proposal(), "accepted")
    store.record(_proposal(), "accepted")

    adjusted = store.adjust_proposal(_proposal())

    assert adjusted["learning_applied"] is True
    assert adjusted["confidence"] > adjusted["base_confidence"]
    assert adjusted["confidence"] <= 0.99


def test_rejected_decisions_can_lower_confidence(tmp_path):
    store = ReasonerLearningStore(tmp_path / "knowledge.sqlite3")
    store.record(_proposal(), "rejected")
    store.record(_proposal(), "rejected")

    adjusted = store.adjust_proposal(_proposal())

    assert adjusted["confidence"] < adjusted["base_confidence"]
    assert adjusted["learning_adjustment"] >= -0.18


def test_single_decision_does_not_overfit(tmp_path):
    store = ReasonerLearningStore(tmp_path / "knowledge.sqlite3")
    store.record(_proposal(), "accepted")

    adjusted = store.adjust_proposal(_proposal())

    assert adjusted["learning_adjustment"] == 0.0


def test_learning_is_persistent(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    store = ReasonerLearningStore(database)
    store.record(_proposal(), "accepted")
    store.record(_proposal(), "accepted")

    reopened = ReasonerLearningStore(database)

    assert reopened.status()["decision_count"] == 2
    assert reopened.adjust_proposal(_proposal())["confidence"] > 0.80
