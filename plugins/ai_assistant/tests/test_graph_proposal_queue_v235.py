import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.knowledge_engine.proposal_store import GraphProposalStore


def _proposal():
    return {
        "kind": "direct_relation",
        "source_id": "one",
        "source_title": "Aquaman",
        "target_id": "two",
        "target_title": "Aquaman and the Lost Kingdom",
        "relation_type": "sequel",
        "confidence": 0.95,
    }


def test_proposal_store_is_persistent_and_deduplicated(tmp_path):
    database = tmp_path / "knowledge.sqlite3"
    store = GraphProposalStore(database)

    first = store.add_many([_proposal()])
    second = store.add_many([_proposal()])

    assert first["created_count"] == 1
    assert second["created_count"] == 0
    assert second["existing_count"] == 1

    reopened = GraphProposalStore(database)
    assert len(reopened.list("pending")) == 1


def test_proposal_can_be_rejected_or_deferred(tmp_path):
    store = GraphProposalStore(tmp_path / "knowledge.sqlite3")
    store.add_many([_proposal()])
    proposal_id = store.list()[0]["id"]

    rejected = store.set_status(proposal_id, "rejected", "Nein")
    assert rejected["status"] == "rejected"
    assert store.list("pending") == []

    deferred = store.set_status(proposal_id, "later", "Später")
    assert deferred["status"] == "later"
    assert len(store.list("later")) == 1
