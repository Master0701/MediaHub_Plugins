import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.semantic_reasoning_engine import SemanticReasoningEngine


def relationship_field(edge_type, source, target, confidence=0.9):
    key = f"supported_relationship:{edge_type}:{source}:{target}"
    return key, {
        "value": {
            "edge_type": edge_type,
            "source_node_key": source,
            "target_node_key": target,
        },
        "confidence": confidence,
        "sources": ["test"],
        "evidence_path": [],
    }


def test_derives_transitive_membership():
    first_key, first = relationship_field(
        "part_of", "movie:a", "franchise:aquaman"
    )
    second_key, second = relationship_field(
        "part_of", "franchise:aquaman", "universe:dceu"
    )
    result = SemanticReasoningEngine.analyze(
        fusion_result={
            "fused_fields": {
                first_key: first,
                second_key: second,
            }
        }
    )
    assert result["summary"]["conclusion_count"] == 1
    item = result["conclusions"][0]
    assert item["source_node_key"] == "movie:a"
    assert item["target_node_key"] == "universe:dceu"
    assert result["automatic_import"] is False


def test_propagates_identity_relationship():
    identity_key, identity = relationship_field(
        "same_as", "character:arthur-curry", "character:aquaman"
    )
    member_key, member = relationship_field(
        "member_of", "character:aquaman", "team:justice-league"
    )
    result = SemanticReasoningEngine.analyze(
        fusion_result={
            "fused_fields": {
                identity_key: identity,
                member_key: member,
            }
        }
    )
    assert any(
        item["source_node_key"] == "character:arthur-curry"
        and item["target_node_key"] == "team:justice-league"
        and item["edge_type"] == "member_of"
        for item in result["conclusions"]
    )


def test_detects_opposing_relationships():
    a_key, a = relationship_field(
        "sequel_of", "movie:b", "movie:a"
    )
    b_key, b = relationship_field(
        "predecessor_of", "movie:b", "movie:a"
    )
    result = SemanticReasoningEngine.analyze(
        fusion_result={"fused_fields": {a_key: a, b_key: b}}
    )
    assert result["summary"]["conflict_count"] == 1
    assert result["decision"]["status"] == "needs_review"
