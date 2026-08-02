from __future__ import annotations

from collections import defaultdict
from typing import Any


class ReasoningIntelligence:
    STRATEGY = "reasoning_intelligence_v510"

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _confidence(cls, value: Any, default: float = 0.5) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number > 1.0:
            number /= 100.0
        return max(0.0, min(1.0, number))

    @classmethod
    def analyze(
        cls,
        *,
        main_node: dict[str, Any],
        groups: dict[str, dict[str, Any]],
        source: dict[str, Any] | None = None,
        graph_validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        graph_validation = dict(graph_validation or {})
        evidence = []
        conclusions = []
        conflicts = []
        alternatives = []
        statements = defaultdict(list)
        pairs = defaultdict(list)
        seen = set()

        for group_name, group in (groups or {}).items():
            if not isinstance(group, dict):
                continue
            entries = list(group.get("edges") or []) + list(
                group.get("observations") or []
            )
            for raw in entries:
                if not isinstance(raw, dict):
                    continue
                edge_type = cls._norm(
                    raw.get("edge_type")
                    or raw.get("relation_type")
                    or raw.get("type")
                ).casefold()
                source_key = cls._norm(
                    raw.get("source_node_key")
                ).casefold()
                target_key = cls._norm(
                    raw.get("target_node_key")
                ).casefold()
                if not edge_type or not source_key or not target_key:
                    continue

                marker = (group_name, edge_type, source_key, target_key)
                if marker in seen:
                    continue
                seen.add(marker)

                item = {
                    "group": group_name,
                    "edge_type": edge_type,
                    "source_node_key": source_key,
                    "target_node_key": target_key,
                    "confidence": cls._confidence(raw.get("confidence")),
                    "reason": cls._norm(raw.get("reason")),
                    "source_id": raw.get("source_id") or source.get("id"),
                    "evidence": cls._norm(
                        raw.get("evidence")
                        or (raw.get("metadata") or {}).get("evidence")
                    ),
                }
                evidence.append(item)
                statements[(edge_type, source_key, target_key)].append(item)
                pairs[(source_key, target_key)].append(item)

        for key, supporting in statements.items():
            edge_type, source_key, target_key = key
            remaining = 1.0
            for item in supporting:
                remaining *= 1.0 - item["confidence"]
            confidence = round(1.0 - remaining, 4)
            groups_used = sorted({item["group"] for item in supporting})
            conclusions.append({
                "conclusion_type": "supported_relationship",
                "edge_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "support_count": len(supporting),
                "supporting_groups": groups_used,
                "evidence_path": supporting,
                "reason": (
                    f"{len(supporting)} evidence item(s) from "
                    f"{len(groups_used)} analysis group(s) support "
                    f"`{edge_type}`."
                ),
                "automatic_import": False,
                "requires_confirmation": True,
            })

        for (source_key, target_key), items in pairs.items():
            relation_types = sorted({item["edge_type"] for item in items})
            if len(relation_types) <= 1:
                continue
            conflicts.append({
                "conflict_type": "relationship_disagreement",
                "source_node_key": source_key,
                "target_node_key": target_key,
                "relation_types": relation_types,
                "evidence_path": items,
                "severity": "review",
                "automatic_resolution": False,
                "requires_confirmation": True,
            })
            alternatives.append({
                "source_node_key": source_key,
                "target_node_key": target_key,
                "options": [
                    {
                        "edge_type": relation,
                        "confidence": max(
                            item["confidence"]
                            for item in items
                            if item["edge_type"] == relation
                        ),
                    }
                    for relation in relation_types
                ],
                "requires_confirmation": True,
            })

        validation_summary = graph_validation.get("summary") or {}
        invalid_count = int(validation_summary.get("invalid_count") or 0)
        warning_count = int(validation_summary.get("warning_count") or 0)
        overall_confidence = (
            round(
                sum(item["confidence"] for item in conclusions)
                / len(conclusions),
                4,
            )
            if conclusions
            else 0.0
        )
        needs_review = bool(
            conflicts or invalid_count or warning_count
        )

        return {
            "strategy": cls.STRATEGY,
            "main_node_key": cls._norm(main_node.get("key")),
            "conclusions": conclusions,
            "conflicts": conflicts,
            "alternatives": alternatives,
            "evidence": evidence,
            "summary": {
                "evidence_count": len(evidence),
                "conclusion_count": len(conclusions),
                "conflict_count": len(conflicts),
                "alternative_count": len(alternatives),
                "overall_confidence": overall_confidence,
                "validation_state": "review" if needs_review else "ok",
                "invalid_graph_items": invalid_count,
                "graph_warnings": warning_count,
            },
            "decision": {
                "status": "needs_review" if needs_review else "supported",
                "confidence": overall_confidence,
                "reason": (
                    "Conflicts or graph warnings require review."
                    if needs_review
                    else "Detected statements are supported by evidence paths."
                ),
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
