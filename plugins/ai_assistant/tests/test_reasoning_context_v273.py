import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.reasoning_context import ReasoningContext, ReasoningContextStore

def test_candidate_can_be_rejected():
    context = ReasoningContext.create({"id": "wiki"})
    evidence = context.add_evidence("Aquaman-Cosplay (2014)", "semantic_engine")
    candidate = context.add_candidate(
        "entity",
        {"title": "Aquaman", "entity_type": "character", "year": 2014},
        0.95,
        "Titel, Typ und Jahr stehen im selben Satz.",
        "semantic_engine",
        evidence["id"],
    )
    context.reject(candidate, "Bildkontext.", "context_filter")
    assert context.rejected[0]["status"] == "rejected"

def test_context_is_persistent(tmp_path):
    context = ReasoningContext.create({"id": "wiki"})
    context.add_trace("scanner", "Dokument geladen.")
    store = ReasoningContextStore(tmp_path / "knowledge.sqlite3")
    path = store.save(context)
    loaded = store.load(context.context_id)
    assert path.exists()
    assert loaded["context_id"] == context.context_id
    assert loaded["trace"][0]["stage"] == "scanner"

def test_questions_and_tasks():
    context = ReasoningContext.create({"id": "wiki"})
    context.add_open_question("Ist 1941 der erste Auftritt?", 90, "context_filter")
    context.add_next_task("resolve_character_first_appearance", {"title": "Aquaman"}, 90, "context_filter")
    assert context.open_questions[0]["status"] == "open"
    assert context.next_tasks[0]["status"] == "pending"
