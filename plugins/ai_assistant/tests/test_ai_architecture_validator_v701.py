import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_architecture_validator import AIArchitectureValidator


def valid_pipeline():
    return {
        name: {}
        for name in AIArchitectureValidator.REQUIRED_PIPELINE_MODULES
    }


def valid_order():
    return [
        "relationship_confidence",
        "character_relationship_graph",
        "character_timeline",
        "character_evolution",
        "character_memory",
        "canonical_conflicts",
        "cross_franchise",
        "canonical_decisions",
        "global_knowledge",
    ]


def test_pipeline_validation_passes():
    result = AIArchitectureValidator._validate_pipeline(
        valid_pipeline()
    )
    assert result["status"] == "ok"
    assert result["missing_modules"] == []


def test_pipeline_validation_detects_missing_module():
    pipeline = valid_pipeline()
    pipeline.pop("global_knowledge")
    result = AIArchitectureValidator._validate_pipeline(pipeline)
    assert result["status"] == "error"
    assert result["missing_modules"] == ["global_knowledge"]


def test_initialization_order_detects_sequence_error():
    order = valid_order()
    order[-1], order[-2] = order[-2], order[-1]
    result = AIArchitectureValidator._validate_initialization_order(
        order
    )
    assert result["status"] == "error"
    assert (
        "canonical_decisions_must_precede_global_knowledge"
        in result["sequence_errors"]
    )


def test_strategy_validation_detects_duplicates():
    result = AIArchitectureValidator._validate_strategies({
        "a": "same_strategy",
        "b": "same_strategy",
    })
    assert result["status"] == "warning"
    assert result["duplicate_strategies"] == ["same_strategy"]
