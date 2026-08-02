from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class PipelineDebugMonitor:
    STRATEGY = "pipeline_debug_monitor_v521"

    MODULES = (
        "scan",
        "structured_preview",
        "parser_result",
        "semantic_result",
        "classified_fields",
        "graph_proposal",
        "graph_merge_preview",
        "relationship_proposal",
        "cast_resolution",
        "character_intelligence",
        "relationship_intelligence",
        "character_relationships",
        "character_identity_fusion",
        "event_intelligence",
        "knowledge_graph",
        "universe_franchise_proposal",
        "franchise_collection",
        "franchise_relations",
        "timeline_order_intelligence",
        "franchise_connection_intelligence",
        "universe_intelligence",
        "character_role_intelligence",
        "character_relationship_intelligence",
        "entity_intelligence",
        "reasoning_intelligence",
        "multi_source_fusion",
        "semantic_reasoning",
        "temporal_causal_intelligence",
        "narrative_extraction",
        "narrative_intelligence",
        "story_arc_linking",
        "story_timeline",
        "franchise_knowledge_graph",
        "character_relationship_graph",
        "entity_resolution_graph",
        "relationship_confidence",
        "character_timeline",
        "character_evolution",
        "character_memory",
        "canonical_conflicts",
        "graph_validation",
    )

    @staticmethod
    def _list_count(value: Any, *keys: str) -> int:
        if not isinstance(value, dict):
            return 0
        return sum(
            len(value.get(key) or [])
            for key in keys
            if isinstance(value.get(key), list)
        )

    @staticmethod
    def _summary(value: Any) -> dict[str, Any]:
        if value is None:
            return {"state": "missing", "available": False}

        if not isinstance(value, dict):
            return {
                "state": "available",
                "available": True,
                "type": type(value).__name__,
            }

        summary = dict(value.get("summary") or {})
        decision = dict(value.get("decision") or {})

        node_count = PipelineDebugMonitor._list_count(
            value, "nodes", "entities"
        )
        edge_count = PipelineDebugMonitor._list_count(
            value, "edges", "relations"
        )
        conflict_count = len(value.get("conflicts") or [])
        warning_count = len(value.get("warnings") or [])
        error_count = len(value.get("errors") or [])

        node_count = node_count or int(summary.get("node_count") or 0)
        edge_count = edge_count or int(summary.get("edge_count") or 0)
        conflict_count = conflict_count or int(
            summary.get("conflict_count") or 0
        )
        warning_count = warning_count or int(
            summary.get("warning_count")
            or summary.get("graph_warnings")
            or 0
        )
        error_count = error_count or int(
            summary.get("error_count")
            or summary.get("invalid_count")
            or summary.get("invalid_graph_items")
            or 0
        )

        confidence = (
            summary.get("overall_confidence")
            if summary.get("overall_confidence") is not None
            else decision.get("confidence")
        )
        state = (
            value.get("state")
            or value.get("status")
            or decision.get("status")
            or ("error" if error_count else "ok")
        )

        return {
            "state": str(state),
            "available": True,
            "strategy": value.get("strategy"),
            "node_count": node_count,
            "edge_count": edge_count,
            "conflict_count": conflict_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "confidence": confidence,
            "requires_confirmation": bool(
                value.get("requires_confirmation", False)
            ),
            "automatic_import": bool(
                value.get("automatic_import", False)
            ),
        }

    @classmethod
    def build(
        cls,
        *,
        modules: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        module_status = {
            name: cls._summary(modules.get(name))
            for name in cls.MODULES
        }

        available_count = sum(
            bool(item.get("available"))
            for item in module_status.values()
        )
        error_count = sum(
            int(item.get("error_count") or 0)
            for item in module_status.values()
        )
        warning_count = sum(
            int(item.get("warning_count") or 0)
            for item in module_status.values()
        )
        conflict_count = sum(
            int(item.get("conflict_count") or 0)
            for item in module_status.values()
        )

        fusion_summary = dict(
            ((modules.get("multi_source_fusion") or {}).get("summary") or {})
        )
        reasoning_summary = dict(
            ((modules.get("reasoning_intelligence") or {}).get("summary") or {})
        )
        validation_summary = dict(
            ((modules.get("graph_validation") or {}).get("summary") or {})
        )

        status = "ok"
        if error_count:
            status = "error"
        elif warning_count or conflict_count:
            status = "review"

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "status": status,
            "modules": module_status,
            "summary": {
                "known_module_count": len(cls.MODULES),
                "available_module_count": available_count,
                "missing_module_count": len(cls.MODULES) - available_count,
                "error_count": error_count,
                "warning_count": warning_count,
                "conflict_count": conflict_count,
                "fusion_field_count": int(
                    fusion_summary.get("field_count") or 0
                ),
                "fusion_evidence_count": int(
                    fusion_summary.get("evidence_count") or 0
                ),
                "fusion_duplicate_count": int(
                    fusion_summary.get("duplicate_count") or 0
                ),
                "reasoning_conclusion_count": int(
                    reasoning_summary.get("conclusion_count") or 0
                ),
                "reasoning_conflict_count": int(
                    reasoning_summary.get("conflict_count") or 0
                ),
                "graph_invalid_count": int(
                    validation_summary.get("invalid_count")
                    or validation_summary.get("invalid_graph_items")
                    or 0
                ),
                "graph_warning_count": int(
                    validation_summary.get("warning_count")
                    or validation_summary.get("graph_warnings")
                    or 0
                ),
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }

    @classmethod
    def format_text(cls, snapshot: dict[str, Any] | None) -> str:
        snapshot = dict(snapshot or {})
        summary = dict(snapshot.get("summary") or {})
        lines = [
            "KI-PIPELINE-DEBUG",
            "=================",
            f"Status: {snapshot.get('status') or 'unbekannt'}",
            (
                "Module vorhanden: "
                f"{summary.get('available_module_count', 0)}/"
                f"{summary.get('known_module_count', len(cls.MODULES))}"
            ),
            f"Fehler: {summary.get('error_count', 0)}",
            f"Warnungen: {summary.get('warning_count', 0)}",
            f"Konflikte: {summary.get('conflict_count', 0)}",
            f"Fusion-Felder: {summary.get('fusion_field_count', 0)}",
            f"Fusion-Belege: {summary.get('fusion_evidence_count', 0)}",
            f"Fusion-Dubletten: {summary.get('fusion_duplicate_count', 0)}",
            (
                "Reasoning-Schlussfolgerungen: "
                f"{summary.get('reasoning_conclusion_count', 0)}"
            ),
            "",
            "MODULE",
            "------",
        ]

        for name, item in (snapshot.get("modules") or {}).items():
            marker = "OK" if item.get("available") else "--"
            details = []
            for key, label in (
                ("node_count", "Nodes"),
                ("edge_count", "Edges"),
                ("conflict_count", "Konflikte"),
                ("warning_count", "Warnungen"),
                ("error_count", "Fehler"),
            ):
                if item.get(key):
                    details.append(f"{label}={item[key]}")
            suffix = f" ({', '.join(details)})" if details else ""
            lines.append(
                f"[{marker}] {name}: "
                f"{item.get('state') or 'unbekannt'}{suffix}"
            )

        return "\n".join(lines)
