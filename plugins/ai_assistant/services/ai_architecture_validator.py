from __future__ import annotations

import importlib
import inspect
from collections import Counter
from typing import Any


class AIArchitectureValidator:
    STRATEGY = "ai_architecture_validator_v701"

    REQUIRED_PIPELINE_MODULES = (
        "semantic_result",
        "entity_resolution_graph",
        "relationship_confidence",
        "character_relationship_graph",
        "character_timeline",
        "character_evolution",
        "character_memory",
        "canonical_conflicts",
        "cross_franchise",
        "canonical_decisions",
        "global_knowledge",
        "graph_validation",
        "pipeline_debug",
    )

    REQUIRED_SERVICE_IMPORTS = (
        ("services.entity_resolution_graph", "EntityResolutionGraph"),
        ("services.relationship_confidence_engine", "RelationshipConfidenceEngine"),
        ("services.character_relationship_graph", "CharacterRelationshipGraph"),
        ("services.character_timeline_engine", "CharacterTimelineEngine"),
        ("services.character_evolution_engine", "CharacterEvolutionEngine"),
        ("services.character_memory_engine", "CharacterMemoryEngine"),
        ("services.canonical_conflict_resolver", "CanonicalConflictResolver"),
        ("services.cross_franchise_resolver", "CrossFranchiseResolver"),
        ("services.canonical_decision_engine", "CanonicalDecisionEngine"),
        ("services.global_knowledge_fusion", "GlobalKnowledgeFusion"),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _validate_imports(cls) -> list[dict[str, Any]]:
        results = []
        for module_name, class_name in cls.REQUIRED_SERVICE_IMPORTS:
            try:
                module = importlib.import_module(module_name)
                service_class = getattr(module, class_name)
                valid = inspect.isclass(service_class)
                error = None if valid else "attribute_is_not_a_class"
            except Exception as exc:
                valid = False
                error = f"{type(exc).__name__}: {exc}"

            results.append({
                "module": module_name,
                "class": class_name,
                "status": "ok" if valid else "error",
                "error": error,
            })
        return results

    @classmethod
    def _validate_strategies(
        cls,
        strategy_map: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = {
            cls._norm(name): cls._norm(value)
            for name, value in (strategy_map or {}).items()
            if cls._norm(name)
        }
        values = [value for value in normalized.values() if value]
        duplicates = sorted(
            value for value, count in Counter(values).items()
            if count > 1
        )
        missing = sorted(
            name for name, value in normalized.items()
            if not value
        )
        return {
            "registered_strategy_count": len(normalized),
            "duplicate_strategies": duplicates,
            "missing_strategies": missing,
            "status": (
                "ok"
                if not duplicates and not missing
                else "warning"
            ),
        }

    @classmethod
    def _validate_pipeline(
        cls,
        pipeline_document: dict[str, Any],
    ) -> dict[str, Any]:
        present = set((pipeline_document or {}).keys())
        missing = [
            name for name in cls.REQUIRED_PIPELINE_MODULES
            if name not in present
        ]
        return {
            "required_module_count": len(
                cls.REQUIRED_PIPELINE_MODULES
            ),
            "present_module_count": (
                len(cls.REQUIRED_PIPELINE_MODULES)
                - len(missing)
            ),
            "missing_modules": missing,
            "status": "ok" if not missing else "error",
        }

    @classmethod
    def _validate_initialization_order(
        cls,
        initialization_order: list[str],
    ) -> dict[str, Any]:
        order = [
            cls._norm(item)
            for item in (initialization_order or [])
            if cls._norm(item)
        ]
        duplicates = sorted(
            name for name, count in Counter(order).items()
            if count > 1
        )

        required_sequence = [
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

        positions = {
            name: index for index, name in enumerate(order)
        }
        sequence_errors = []
        for left, right in zip(
            required_sequence,
            required_sequence[1:],
        ):
            if left in positions and right in positions:
                if positions[left] >= positions[right]:
                    sequence_errors.append(
                        f"{left}_must_precede_{right}"
                    )

        missing = [
            name for name in required_sequence
            if name not in positions
        ]

        return {
            "initialization_count": len(order),
            "duplicate_initializations": duplicates,
            "missing_initializations": missing,
            "sequence_errors": sequence_errors,
            "status": (
                "ok"
                if not duplicates
                and not missing
                and not sequence_errors
                else "error"
            ),
        }

    @classmethod
    def build(
        cls,
        *,
        pipeline_document: dict[str, Any],
        strategy_map: dict[str, Any],
        initialization_order: list[str],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        imports = cls._validate_imports()
        strategies = cls._validate_strategies(strategy_map)
        pipeline = cls._validate_pipeline(pipeline_document)
        initialization = cls._validate_initialization_order(
            initialization_order
        )

        import_errors = [
            item for item in imports
            if item["status"] != "ok"
        ]

        errors = []
        warnings = []

        if import_errors:
            errors.append("service_import_errors")
        if pipeline["status"] != "ok":
            errors.append("pipeline_incomplete")
        if initialization["status"] != "ok":
            errors.append("initialization_order_invalid")
        if strategies["status"] != "ok":
            warnings.append("strategy_registration_warning")

        if errors:
            overall_status = "fail"
        elif warnings:
            overall_status = "warn"
        else:
            overall_status = "pass"

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "status": overall_status,
            "checks": {
                "imports": imports,
                "strategies": strategies,
                "pipeline": pipeline,
                "initialization_order": initialization,
            },
            "summary": {
                "required_service_count": len(
                    cls.REQUIRED_SERVICE_IMPORTS
                ),
                "import_error_count": len(import_errors),
                "missing_pipeline_module_count": len(
                    pipeline["missing_modules"]
                ),
                "duplicate_strategy_count": len(
                    strategies["duplicate_strategies"]
                ),
                "initialization_error_count": (
                    len(initialization["duplicate_initializations"])
                    + len(initialization["missing_initializations"])
                    + len(initialization["sequence_errors"])
                ),
                "error_count": len(errors),
                "warning_count": len(warnings),
            },
            "errors": errors,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
