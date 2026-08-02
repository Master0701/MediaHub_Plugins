from __future__ import annotations

from collections import defaultdict
from typing import Any


class SemanticReasoningEngine:
    STRATEGY = "semantic_reasoning_engine_v530"

    TRANSITIVE_RELATIONS = {
        "belongs_to_universe",
        "installment_of",
        "part_of",
        "member_of",
    }
    IDENTITY_RELATIONS = {
        "same_as",
        "alias_of",
        "portrays",
        "identity_of",
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
    ) -> list[dict[str, Any]]:
        relationships = []
        for field, item in (fusion_result.get("fused_fields") or {}).items():
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if not isinstance(value, dict):
                continue
            edge_type = cls._norm(value.get("edge_type")).casefold()
            source_key = cls._norm(value.get("source_node_key"))
            target_key = cls._norm(value.get("target_node_key"))
            if not edge_type or not source_key or not target_key:
                continue
            relationships.append({
                "field": field,
                "edge_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": cls._confidence(item.get("confidence")),
                "sources": list(item.get("sources") or []),
                "evidence_path": list(item.get("evidence_path") or []),
            })
        return relationships

    @staticmethod
    def _key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("edge_type") or ""),
            str(item.get("source_node_key") or ""),
            str(item.get("target_node_key") or ""),
        )

    @classmethod
    def _derive_identity_propagation(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        aliases: dict[str, set[str]] = defaultdict(set)
        outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for item in relationships:
            outgoing[item["source_node_key"]].append(item)
            if item["edge_type"] in cls.IDENTITY_RELATIONS:
                aliases[item["source_node_key"]].add(item["target_node_key"])
                aliases[item["target_node_key"]].add(item["source_node_key"])

        conclusions = []
        for identity, linked in aliases.items():
            for alias in linked:
                for relation in outgoing.get(alias, []):
                    if relation["edge_type"] in cls.IDENTITY_RELATIONS:
                        continue
                    conclusions.append({
                        "conclusion_type": "identity_propagation",
                        "edge_type": relation["edge_type"],
                        "source_node_key": identity,
                        "target_node_key": relation["target_node_key"],
                        "confidence": round(
                            min(relation["confidence"], 0.82),
                            4,
                        ),
                        "reason": (
                            f"{identity} ist über eine Identitätsbeziehung "
                            f"mit {alias} verbunden; dessen Beziehung "
                            f"{relation['edge_type']} wurde übertragen."
                        ),
                        "evidence_path": [
                            {
                                "kind": "identity_link",
                                "source_node_key": identity,
                                "target_node_key": alias,
                            },
                            {
                                "kind": "relationship",
                                "edge_type": relation["edge_type"],
                                "source_node_key": alias,
                                "target_node_key": relation["target_node_key"],
                            },
                        ],
                        "requires_confirmation": True,
                    })
        return conclusions

    @classmethod
    def _derive_transitive_relations(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relationships:
            if item["edge_type"] in cls.TRANSITIVE_RELATIONS:
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
                        "conclusion_type": "transitive_relationship",
                        "edge_type": edge_type,
                        "source_node_key": first["source_node_key"],
                        "target_node_key": second["target_node_key"],
                        "confidence": round(
                            min(
                                first["confidence"],
                                second["confidence"],
                            ) * 0.86,
                            4,
                        ),
                        "reason": (
                            f"{first['source_node_key']} steht über "
                            f"{first['target_node_key']} transitiv in der "
                            f"Beziehung {edge_type} zu "
                            f"{second['target_node_key']}."
                        ),
                        "evidence_path": [
                            {
                                "kind": "relationship",
                                "edge_type": edge_type,
                                "source_node_key": first["source_node_key"],
                                "target_node_key": first["target_node_key"],
                            },
                            {
                                "kind": "relationship",
                                "edge_type": edge_type,
                                "source_node_key": second["source_node_key"],
                                "target_node_key": second["target_node_key"],
                            },
                        ],
                        "requires_confirmation": True,
                    })
        return conclusions

    @classmethod
    def _find_conflicts(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        opposites = {
            "predecessor_of": "sequel_of",
            "sequel_of": "predecessor_of",
            "parent_of": "child_of",
            "child_of": "parent_of",
        }
        known = {cls._key(item): item for item in relationships}
        conflicts = []
        seen = set()

        for item in relationships:
            opposite = opposites.get(item["edge_type"])
            if not opposite:
                continue
            reverse_key = (
                opposite,
                item["source_node_key"],
                item["target_node_key"],
            )
            if reverse_key not in known:
                continue
            key = tuple(sorted((item["edge_type"], opposite))) + (
                item["source_node_key"],
                item["target_node_key"],
            )
            if key in seen:
                continue
            seen.add(key)
            conflicts.append({
                "conflict_type": "opposing_relationships",
                "source_node_key": item["source_node_key"],
                "target_node_key": item["target_node_key"],
                "relationship_a": item["edge_type"],
                "relationship_b": opposite,
                "reason": (
                    "Für dasselbe gerichtete Knotenpaar wurden "
                    "gegensätzliche Beziehungen gefunden."
                ),
                "requires_confirmation": True,
            })
        return conflicts

    @classmethod
    def analyze(
        cls,
        *,
        fusion_result: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relationships = cls._collect_relationships(fusion_result)
        conclusions = (
            cls._derive_identity_propagation(relationships)
            + cls._derive_transitive_relations(relationships)
        )

        existing = {cls._key(item) for item in relationships}
        seen = set()
        unique = []
        for item in conclusions:
            key = cls._key(item)
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
