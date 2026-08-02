import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_knowledge_graph import FranchiseKnowledgeGraph


def test_creates_universe_node_and_edge():
    result = FranchiseKnowledgeGraph.build(
        semantic_result={
            "primary_title": "Aquaman: Lost Kingdom",
            "primary_entity_type": "movie",
            "metadata": {
                "universe": "DC Extended Universe",
            },
            "relation_proposals": [],
        },
        semantic_reasoning={},
        temporal_causal_intelligence={},
        narrative_intelligence={},
        story_arc_linking={},
        story_timeline={},
    )

    assert result["summary"]["universe_node_count"] == 1
    assert any(
        edge["edge_type"] == "belongs_to_universe"
        for edge in result["edges"]
    )
    assert result["automatic_import"] is False


def test_collects_sequel_relation():
    result = FranchiseKnowledgeGraph.build(
        semantic_result={
            "primary_title": "Aquaman: Lost Kingdom",
            "primary_entity_type": "movie",
            "relation_proposals": [
                {
                    "id": "1",
                    "relation_type": "sequel",
                    "target_title": "Aquaman",
                    "confidence": 0.7,
                }
            ],
        },
        semantic_reasoning={},
        temporal_causal_intelligence={},
        narrative_intelligence={},
        story_arc_linking={},
        story_timeline={},
    )

    assert any(
        edge["edge_type"] == "sequel"
        for edge in result["edges"]
    )


def test_collects_alternate_timeline_edge():
    result = FranchiseKnowledgeGraph.build(
        semantic_result={
            "primary_title": "Example",
            "primary_entity_type": "movie",
            "relation_proposals": [],
        },
        semantic_reasoning={
            "strategy": "semantic_reasoning_engine_v530",
            "conclusions": [
                {
                    "edge_type": "alternate_timeline",
                    "source_node_key": "media:a",
                    "target_node_key": "timeline:b",
                    "confidence": 0.8,
                }
            ],
        },
        temporal_causal_intelligence={},
        narrative_intelligence={},
        story_arc_linking={},
        story_timeline={},
    )

    assert result["summary"]["canon_edge_count"] == 1
