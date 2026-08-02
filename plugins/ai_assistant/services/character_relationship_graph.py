from __future__ import annotations

from collections import defaultdict
from typing import Any


class CharacterRelationshipGraph:
    STRATEGY = "character_relationship_graph_v600"

    RELATION_TYPES = {
        "father_of",
        "mother_of",
        "parent_of",
        "child_of",
        "son_of",
        "daughter_of",
        "brother_of",
        "sister_of",
        "sibling_of",
        "spouse_of",
        "friend_of",
        "enemy_of",
        "mentor_of",
        "student_of",
        "team_member_of",
        "allied_with",
        "betrays",
        "leader_of",
        "serves",
        "alias_of",
        "secret_identity_of",
        "same_identity_as",
    }

    SYMMETRIC_RELATIONS = {
        "sibling_of",
        "spouse_of",
        "friend_of",
        "enemy_of",
        "allied_with",
        "same_identity_as",
    }

    INVERSE_RELATIONS = {
        "father_of": "child_of",
        "mother_of": "child_of",
        "parent_of": "child_of",
        "son_of": "parent_of",
        "daughter_of": "parent_of",
        "child_of": "parent_of",
        "mentor_of": "student_of",
        "student_of": "mentor_of",
        "leader_of": "serves",
        "serves": "leader_of",
        "alias_of": "same_identity_as",
        "secret_identity_of": "same_identity_as",
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
    def _collect_edges(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        edges = []

        for payload in payloads:
            items = (
                payload.get("conclusions")
                or payload.get("relations")
                or payload.get("edges")
                or payload.get("arcs")
                or []
            )
            for item in items:
                if not isinstance(item, dict):
                    continue

                edge_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                ).casefold()
                source = cls._norm(
                    item.get("source_node_key")
                    or item.get("owner_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("end_node_key")
                )

                if edge_type not in cls.RELATION_TYPES:
                    continue
                if not source or not target:
                    continue

                edges.append({
                    "edge_type": edge_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "confidence": cls._confidence(
                        item.get("confidence")
                    ),
                    "origin": payload.get("strategy"),
                    "requires_confirmation": True,
                })

        return edges

    @classmethod
    def _derive_edges(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        derived = []

        for edge in edges:
            relation = edge["edge_type"]
            source = edge["source_node_key"]
            target = edge["target_node_key"]
            confidence = round(edge["confidence"] * 0.92, 4)

            if relation in cls.SYMMETRIC_RELATIONS:
                derived.append({
                    "edge_type": relation,
                    "source_node_key": target,
                    "target_node_key": source,
                    "confidence": confidence,
                    "origin": "derived_symmetric_relation",
                    "requires_confirmation": True,
                })

            inverse = cls.INVERSE_RELATIONS.get(relation)
            if inverse:
                derived.append({
                    "edge_type": inverse,
                    "source_node_key": target,
                    "target_node_key": source,
                    "confidence": confidence,
                    "origin": "derived_inverse_relation",
                    "requires_confirmation": True,
                })

        return derived

    @classmethod
    def _find_conflicts(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        known = {
            (
                edge["edge_type"],
                edge["source_node_key"],
                edge["target_node_key"],
            )
            for edge in edges
        }

        opposing = {
            "friend_of": "enemy_of",
            "enemy_of": "friend_of",
            "allied_with": "betrays",
            "betrays": "allied_with",
            "mentor_of": "enemy_of",
        }

        conflicts = []
        seen = set()

        for edge in edges:
            opposite = opposing.get(edge["edge_type"])
            if not opposite:
                continue

            key = (
                opposite,
                edge["source_node_key"],
                edge["target_node_key"],
            )
            if key not in known:
                continue

            conflict_key = (
                *sorted((
                    edge["source_node_key"],
                    edge["target_node_key"],
                )),
                *sorted((edge["edge_type"], opposite)),
            )
            if conflict_key in seen:
                continue
            seen.add(conflict_key)

            conflicts.append({
                "conflict_type": "character_relationship_contradiction",
                "source_node_key": edge["source_node_key"],
                "target_node_key": edge["target_node_key"],
                "relationship_a": edge["edge_type"],
                "relationship_b": opposite,
                "requires_confirmation": True,
            })

        return conflicts

    @classmethod
    def build(
        cls,
        *,
        relationship_intelligence: dict[str, Any],
        character_relationship_intelligence: dict[str, Any],
        character_relationship_engine: dict[str, Any],
        franchise_knowledge_graph: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        edges = cls._collect_edges(
            relationship_intelligence,
            character_relationship_intelligence,
            character_relationship_engine,
            franchise_knowledge_graph,
        )

        edges += cls._derive_edges(edges)

        unique_edges = []
        seen = set()
        for edge in edges:
            key = (
                edge["edge_type"],
                edge["source_node_key"],
                edge["target_node_key"],
            )
            if key in seen:
                continue
            seen.add(key)
            unique_edges.append(edge)

        nodes = {}
        for edge in unique_edges:
            for node_key in (
                edge["source_node_key"],
                edge["target_node_key"],
            ):
                if node_key not in nodes:
                    if node_key.startswith("character:"):
                        node_type = "character"
                    elif node_key.startswith("team:"):
                        node_type = "team"
                    elif node_key.startswith("organization:"):
                        node_type = "organization"
                    elif node_key.startswith("identity:"):
                        node_type = "identity"
                    else:
                        node_type = "character_or_group"
                    nodes[node_key] = {
                        "id": node_key,
                        "node_type": node_type,
                        "title": node_key.split(":", 1)[-1],
                    }

        grouped = defaultdict(int)
        for edge in unique_edges:
            grouped[edge["edge_type"]] += 1

        conflicts = cls._find_conflicts(unique_edges)

        confidence = (
            round(
                sum(edge["confidence"] for edge in unique_edges)
                / len(unique_edges),
                4,
            )
            if unique_edges
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
            "nodes": list(nodes.values()),
            "edges": unique_edges,
            "conflicts": conflicts,
            "relation_counts": dict(sorted(grouped.items())),
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(unique_edges),
                "character_node_count": sum(
                    node["node_type"] == "character"
                    for node in nodes.values()
                ),
                "identity_edge_count": sum(
                    edge["edge_type"] in {
                        "alias_of",
                        "secret_identity_of",
                        "same_identity_as",
                    }
                    for edge in unique_edges
                ),
                "family_edge_count": sum(
                    edge["edge_type"] in {
                        "father_of",
                        "mother_of",
                        "parent_of",
                        "child_of",
                        "son_of",
                        "daughter_of",
                        "brother_of",
                        "sister_of",
                        "sibling_of",
                        "spouse_of",
                    }
                    for edge in unique_edges
                ),
                "conflict_count": len(conflicts),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if unique_edges or conflicts
                    else "no_character_relationships"
                ),
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
