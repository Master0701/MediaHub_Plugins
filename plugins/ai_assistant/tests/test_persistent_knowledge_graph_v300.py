import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.persistent_knowledge_graph import PersistentKnowledgeGraphStore

def proposal():
    return {
        "main_node_key": "movie:aquaman: lost kingdom:2023",
        "nodes": [
            {
                "key": "movie:aquaman: lost kingdom:2023",
                "node_type": "movie",
                "title": "Aquaman: Lost Kingdom",
                "year": 2023,
                "metadata": {"runtime_minutes": 124},
                "confidence": 0.89,
            },
            {
                "key": "movie:aquaman:2018",
                "node_type": "movie",
                "title": "Aquaman",
                "year": 2018,
                "metadata": {},
                "confidence": 0.92,
            },
        ],
        "edges": [
            {
                "edge_type": "sequel_of",
                "source_node_key": "movie:aquaman: lost kingdom:2023",
                "target_node_key": "movie:aquaman:2018",
                "confidence": 0.92,
            }
        ],
    }

def test_preview_confirm_and_existing(tmp_path):
    store = PersistentKnowledgeGraphStore(tmp_path / "knowledge.sqlite3")
    preview = store.preview_merge(proposal())
    assert len(preview["new_nodes"]) == 2
    assert len(preview["new_edges"]) == 1

    result = store.confirm_merge(proposal(), "Bestätigt")
    assert result["total_nodes"] == 2
    assert result["total_edges"] == 1

    preview2 = store.preview_merge(proposal())
    assert len(preview2["existing_nodes"]) == 2
    assert len(preview2["existing_edges"]) == 1

def test_resolve_node(tmp_path):
    store = PersistentKnowledgeGraphStore(tmp_path / "knowledge.sqlite3")
    store.confirm_merge(proposal())
    result = store.resolve_node("Aquaman", "movie", 2018)
    assert len(result) == 1
    assert result[0]["key"] == "movie:aquaman:2018"
