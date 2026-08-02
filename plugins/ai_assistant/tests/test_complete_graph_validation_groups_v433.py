import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_engine.knowledge_graph_merge_validator import (
    KnowledgeGraphMergeValidator,
)


PLUGIN_PATH = ROOT / "plugin.py"

EXPECTED_GROUPS = {
    "graph_proposal",
    "relationship_proposal",
    "cast_resolution",
    "character_intelligence",
    "relationship_intelligence",
    "event_intelligence",
    "character_relationships",
    "character_identity_fusion",
    "universe_franchise_proposal",
    "universe_intelligence",
    "character_role_intelligence",
    "character_relationship_intelligence",
    "franchise_collection",
    "franchise_relations",
    "timeline_order_intelligence",
    "franchise_connection_intelligence",
}


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_text())


def _validation_group_names() -> set[str]:
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Assign):
            continue

        if not any(
            isinstance(target, ast.Name)
            and target.id == "graph_validation_groups"
            for target in node.targets
        ):
            continue

        value = node.value
        assert isinstance(value, ast.ListComp)

        generator = value.generators[0]
        iterator = generator.iter
        assert isinstance(iterator, ast.Tuple)

        return {
            item.id
            for item in iterator.elts
            if isinstance(item, ast.Name)
        }

    raise AssertionError(
        "graph_validation_groups-Zuweisung nicht gefunden."
    )


def test_plugin_syntax_is_valid():
    _tree()


def test_all_scan_graph_groups_are_validated():
    assert _validation_group_names() == EXPECTED_GROUPS


def test_legacy_character_graph_name_is_absent():
    assert "character_graph" not in _text()


def test_runtime_merge_accepts_all_ten_groups():
    groups = [
        {
            "nodes": [{
                "key": f"test:node:{index}",
                "node_type": "test",
                "title": f"Node {index}",
            }],
            "edges": [],
        }
        for index in range(10)
    ]

    result = KnowledgeGraphMergeValidator.merge(
        graph_groups=groups,
    )

    assert result["group_count"] == 10
    assert result["node_count"] == 10
    assert result["conflict_count"] == 0
    assert result["dangling_edge_count"] == 0


def test_cast_and_relationship_edges_are_validated():
    main = {
        "nodes": [
            {
                "key": "movie:aquaman:2023",
                "node_type": "movie",
                "title": "Aquaman: Lost Kingdom",
            },
            {
                "key": "person:jason momoa",
                "node_type": "person",
                "title": "Jason Momoa",
            },
            {
                "key": "character:arthur curry",
                "node_type": "character",
                "title": "Arthur Curry",
            },
        ],
        "edges": [],
    }
    cast = {
        "nodes": [],
        "edges": [{
            "edge_type": "portrays",
            "source_node_key": "person:jason momoa",
            "target_node_key": "character:arthur curry",
        }],
    }
    relationship = {
        "nodes": [],
        "edges": [{
            "edge_type": "appears_in",
            "source_node_key": "character:arthur curry",
            "target_node_key": "movie:aquaman:2023",
        }],
    }

    result = KnowledgeGraphMergeValidator.merge(
        graph_groups=[main, cast, relationship],
    )

    edge_types = {
        edge["edge_type"]
        for edge in result["edges"]
    }

    assert {"portrays", "appears_in"} <= edge_types
    assert result["dangling_edge_count"] == 0


def test_plugin_version_constant_exists():
    text = _text()

    assert 'VERSION = "' in text
