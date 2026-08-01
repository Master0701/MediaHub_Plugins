import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.knowledge_engine.knowledge_graph_merge_validator import (
    KnowledgeGraphMergeValidator,
)


def merge(*groups):
    return KnowledgeGraphMergeValidator.merge(
        graph_groups=list(groups),
    )


def test_duplicate_nodes_are_merged():
    result = merge(
        {
            "nodes": [{
                "key": "character:arthur curry",
                "node_type": "character",
                "title": "Arthur Curry",
                "confidence": 0.8,
                "source_id": "wiki",
            }],
            "edges": [],
        },
        {
            "nodes": [{
                "key": "character:arthur curry",
                "node_type": "character",
                "title": "Arthur Curry",
                "confidence": 0.95,
                "source_id": "tmdb",
            }],
            "edges": [],
        },
    )

    assert result["node_count"] == 1
    node = result["nodes"][0]
    assert node["confidence"] == 0.95
    assert node["source_ids"] == ["wiki", "tmdb"]


def test_duplicate_edges_are_merged():
    result = merge(
        {
            "nodes": [
                {
                    "key": "movie:a",
                    "node_type": "movie",
                    "title": "A",
                },
                {
                    "key": "franchise:a",
                    "node_type": "franchise",
                    "title": "A",
                },
            ],
            "edges": [{
                "edge_type": "installment_of",
                "source_node_key": "movie:a",
                "target_node_key": "franchise:a",
                "confidence": 0.7,
                "source_id": "wiki",
            }],
        },
        {
            "nodes": [],
            "edges": [{
                "edge_type": "installment_of",
                "source_node_key": "movie:a",
                "target_node_key": "franchise:a",
                "confidence": 0.9,
                "source_id": "tmdb",
            }],
        },
    )

    assert result["edge_count"] == 1
    edge = result["edges"][0]
    assert edge["confidence"] == 0.9
    assert edge["source_ids"] == ["wiki", "tmdb"]


def test_node_title_conflict_is_reported():
    result = merge(
        {
            "nodes": [{
                "key": "movie:aquaman:2023",
                "node_type": "movie",
                "title": "Aquaman: Lost Kingdom",
            }],
            "edges": [],
        },
        {
            "nodes": [{
                "key": "movie:aquaman:2023",
                "node_type": "movie",
                "title": "Aquaman and the Lost Kingdom",
            }],
            "edges": [],
        },
    )

    assert result["conflict_count"] == 1
    assert result["conflicts"][0]["field"] == "title"


def test_node_year_conflict_is_reported():
    result = merge(
        {
            "nodes": [{
                "key": "movie:example",
                "node_type": "movie",
                "title": "Example",
                "year": 2020,
            }],
            "edges": [],
        },
        {
            "nodes": [{
                "key": "movie:example",
                "node_type": "movie",
                "title": "Example",
                "year": 2021,
            }],
            "edges": [],
        },
    )

    assert result["conflict_count"] == 1
    assert result["conflicts"][0]["field"] == "year"


def test_metadata_is_combined():
    result = merge(
        {
            "nodes": [{
                "key": "character:arthur",
                "node_type": "character",
                "title": "Arthur",
                "metadata": {"alias": "Aquaman"},
            }],
            "edges": [],
        },
        {
            "nodes": [{
                "key": "character:arthur",
                "node_type": "character",
                "title": "Arthur",
                "metadata": {"alias": "King of Atlantis"},
            }],
            "edges": [],
        },
    )

    assert result["nodes"][0]["metadata"]["alias"] == [
        "Aquaman",
        "King of Atlantis",
    ]


def test_dangling_source_edge_is_reported():
    result = merge({
        "nodes": [{
            "key": "franchise:a",
            "node_type": "franchise",
            "title": "A",
        }],
        "edges": [{
            "edge_type": "installment_of",
            "source_node_key": "movie:a",
            "target_node_key": "franchise:a",
        }],
    })

    assert result["dangling_edge_count"] == 1
    assert result["dangling_edges"][0]["missing"] == ["source"]


def test_dangling_target_edge_is_reported():
    result = merge({
        "nodes": [{
            "key": "movie:a",
            "node_type": "movie",
            "title": "A",
        }],
        "edges": [{
            "edge_type": "installment_of",
            "source_node_key": "movie:a",
            "target_node_key": "franchise:a",
        }],
    })

    assert result["dangling_edge_count"] == 1
    assert result["dangling_edges"][0]["missing"] == ["target"]


def test_complete_edge_has_no_dangling_warning():
    result = merge({
        "nodes": [
            {
                "key": "movie:a",
                "node_type": "movie",
                "title": "A",
            },
            {
                "key": "franchise:a",
                "node_type": "franchise",
                "title": "A",
            },
        ],
        "edges": [{
            "edge_type": "installment_of",
            "source_node_key": "movie:a",
            "target_node_key": "franchise:a",
        }],
    })

    assert result["dangling_edge_count"] == 0


def test_invalid_nodes_are_skipped():
    result = merge({
        "nodes": [
            {},
            {"key": "movie:a"},
            {"node_type": "movie"},
        ],
        "edges": [],
    })

    assert result["node_count"] == 0
    assert len(result["warnings"]) == 3


def test_invalid_edges_are_skipped():
    result = merge({
        "nodes": [],
        "edges": [
            {},
            {"edge_type": "sequel_of"},
        ],
    })

    assert result["edge_count"] == 0
    assert len(result["warnings"]) == 2


def test_non_dict_group_is_skipped():
    result = KnowledgeGraphMergeValidator.merge(
        graph_groups=[None, "invalid", {"nodes": [], "edges": []}],
    )

    assert result["group_count"] == 1
    assert len(result["warnings"]) == 2


def test_confirmation_is_forced_for_nodes_and_edges():
    result = merge({
        "nodes": [
            {
                "key": "movie:a",
                "node_type": "movie",
                "title": "A",
                "requires_confirmation": False,
                "automatic_import": True,
            },
            {
                "key": "franchise:a",
                "node_type": "franchise",
                "title": "A",
            },
        ],
        "edges": [{
            "edge_type": "installment_of",
            "source_node_key": "movie:a",
            "target_node_key": "franchise:a",
            "requires_confirmation": False,
            "automatic_import": True,
        }],
    })

    assert all(
        node["requires_confirmation"] is True
        and node["automatic_import"] is False
        for node in result["nodes"]
    )
    assert all(
        edge["requires_confirmation"] is True
        and edge["automatic_import"] is False
        for edge in result["edges"]
    )


def test_empty_input_is_supported():
    result = merge()

    assert result["node_count"] == 0
    assert result["edge_count"] == 0
    assert result["conflict_count"] == 0


def test_strategy_and_schema():
    result = merge()

    assert result["schema_version"] == 1
    assert result["strategy"].startswith(
        "knowledge_graph_merge_validator_v"
    )
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
