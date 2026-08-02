from __future__ import annotations

from collections import defaultdict
from typing import Any


class TemporalCausalIntelligence:
    STRATEGY = "temporal_causal_intelligence_v540"

    TEMPORAL_RELATIONS = {
        "happens_before",
        "happens_after",
        "takes_place_before",
        "takes_place_after",
        "released_before",
        "released_after",
        "predecessor_of",
        "sequel_of",
    }

    CAUSAL_RELATIONS = {
        "causes",
        "caused_by",
        "leads_to",
        "results_in",
        "triggered_by",
    }

    OPPOSITE_RELATIONS = {
        "happens_before": "happens_after",
        "happens_after": "happens_before",
        "takes_place_before": "takes_place_after",
        "takes_place_after": "takes_place_before",
        "released_before": "released_after",
        "released_after": "released_before",
        "predecessor_of": "sequel_of",
        "sequel_of": "predecessor_of",
        "causes": "caused_by",
        "caused_by": "causes",
    }

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
    def _collect_relationships(
        cls,
        fusion_result: dict[str, Any],
        semantic_reasoning: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []

        for item in (fusion_result.get("fused_fields") or {}).values():
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if not isinstance(value, dict):
                continue
            edge_type = cls._norm(value.get("edge_type")).casefold()
            source_key = cls._norm(value.get("source_node_key"))
            target_key = cls._norm(value.get("target_node_key"))
            if edge_type and source_key and target_key:
                relationships.append({
                    "edge_type": edge_type,
                    "source_node_key": source_key,
                    "target_node_key": target_key,
                    "confidence": cls._confidence(item.get("confidence")),
                    "origin": "multi_source_fusion",
                })

        for item in semantic_reasoning.get("conclusions") or []:
            if not isinstance(item, dict):
                continue
            edge_type = cls._norm(item.get("edge_type")).casefold()
            source_key = cls._norm(item.get("source_node_key"))
            target_key = cls._norm(item.get("target_node_key"))
            if edge_type and source_key and target_key:
                relationships.append({
                    "edge_type": edge_type,
                    "source_node_key": source_key,
                    "target_node_key": target_key,
                    "confidence": cls._confidence(item.get("confidence")),
                    "origin": "semantic_reasoning",
                })

        unique = {}
        for item in relationships:
            key = (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            previous = unique.get(key)
            if previous is None or item["confidence"] > previous["confidence"]:
                unique[key] = item
        return list(unique.values())

    @classmethod
    def _derive_temporal_chains(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relationships:
            if item["edge_type"] in cls.TEMPORAL_RELATIONS:
                by_type[item["edge_type"]].append(item)

        conclusions = []
        for edge_type, items in by_type.items():
            outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in items:
                outgoing[item["source_node_key"]].append(item)

            for first in items:
                for second in outgoing.get(first["target_node_key"], []):
                    if first["source_node_key"] == second["target_node_key"]:
                        continue
                    conclusions.append({
                        "conclusion_type": "temporal_chain",
                        "edge_type": edge_type,
                        "source_node_key": first["source_node_key"],
                        "target_node_key": second["target_node_key"],
                        "confidence": round(
                            min(
                                first["confidence"],
                                second["confidence"],
                            ) * 0.84,
                            4,
                        ),
                        "reason": (
                            f"{first['source_node_key']} steht über "
                            f"{first['target_node_key']} zeitlich vor/nach "
                            f"{second['target_node_key']}."
                        ),
                        "evidence_path": [
                            dict(first),
                            dict(second),
                        ],
                        "requires_confirmation": True,
                    })
        return conclusions

    @classmethod
    def _derive_causal_chains(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        direct = [
            item
            for item in relationships
            if item["edge_type"] in cls.CAUSAL_RELATIONS
        ]
        outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in direct:
            outgoing[item["source_node_key"]].append(item)

        conclusions = []
        for first in direct:
            for second in outgoing.get(first["target_node_key"], []):
                if first["source_node_key"] == second["target_node_key"]:
                    continue
                conclusions.append({
                    "conclusion_type": "causal_chain",
                    "edge_type": "leads_to",
                    "source_node_key": first["source_node_key"],
                    "target_node_key": second["target_node_key"],
                    "confidence": round(
                        min(
                            first["confidence"],
                            second["confidence"],
                        ) * 0.8,
                        4,
                    ),
                    "reason": (
                        f"{first['source_node_key']} führt über "
                        f"{first['target_node_key']} zu "
                        f"{second['target_node_key']}."
                    ),
                    "evidence_path": [
                        dict(first),
                        dict(second),
                    ],
                    "requires_confirmation": True,
                })
        return conclusions

    @classmethod
    def _find_conflicts(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        known = {
            (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            for item in relationships
        }
        conflicts = []
        seen = set()

        for item in relationships:
            opposite = cls.OPPOSITE_RELATIONS.get(item["edge_type"])
            if not opposite:
                continue
            opposite_key = (
                opposite,
                item["source_node_key"],
                item["target_node_key"],
            )
            if opposite_key not in known:
                continue

            key = (
                item["source_node_key"],
                item["target_node_key"],
                *sorted((item["edge_type"], opposite)),
            )
            if key in seen:
                continue
            seen.add(key)

            conflicts.append({
                "conflict_type": "temporal_or_causal_contradiction",
                "source_node_key": item["source_node_key"],
                "target_node_key": item["target_node_key"],
                "relationship_a": item["edge_type"],
                "relationship_b": opposite,
                "reason": (
                    "Für dasselbe gerichtete Knotenpaar wurden "
                    "widersprüchliche zeitliche oder kausale Beziehungen "
                    "gefunden."
                ),
                "requires_confirmation": True,
            })

        return conflicts

    @classmethod
    def analyze(
        cls,
        *,
        fusion_result: dict[str, Any],
        semantic_reasoning: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relationships = cls._collect_relationships(
            fusion_result,
            semantic_reasoning,
        )

        conclusions = (
            cls._derive_temporal_chains(relationships)
            + cls._derive_causal_chains(relationships)
        )

        existing = {
            (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            for item in relationships
        }
        unique = []
        seen = set()
        for item in conclusions:
            key = (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            if key in existing or key in seen:
                continue
            seen.add(key)
            unique.append(item)

        conflicts = cls._find_conflicts(relationships)
        confidence = (
            round(
                sum(item["confidence"] for item in unique) / len(unique),
                4,
            )
            if unique
            else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "conclusions": unique,
            "conflicts": conflicts,
            "summary": {
                "input_relationship_count": len(relationships),
                "temporal_relationship_count": sum(
                    item["edge_type"] in cls.TEMPORAL_RELATIONS
                    for item in relationships
                ),
                "causal_relationship_count": sum(
                    item["edge_type"] in cls.CAUSAL_RELATIONS
                    for item in relationships
                ),
                "conclusion_count": len(unique),
                "conflict_count": len(conflicts),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if conflicts or unique
                    else "no_new_conclusions"
                ),
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
