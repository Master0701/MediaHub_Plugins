from __future__ import annotations

from collections import defaultdict
from typing import Any


class RelationshipConsistencyChecker:
    STRATEGY = "relationship_consistency_checker_v704"

    INVERSE_RELATIONS = {
        "parent_of": "child_of",
        "child_of": "parent_of",
        "portrayed_by": "portrays",
        "portrays": "portrayed_by",
        "prequel_of": "sequel_of",
        "sequel_of": "prequel_of",
    }

    SYMMETRIC_RELATIONS = {
        "sibling_of",
        "married_to",
        "partner_of",
        "ally_of",
        "enemy_of",
        "crosses_over_with",
        "parallel_universe_of",
        "non_canon_to",
    }

    EXCLUSIVE_RELATIONS = {
        "married_to",
        "partner_of",
        "belongs_to_universe",
        "belongs_to_timeline",
    }

    CONTRADICTORY_PAIRS = {
        frozenset(("ally_of", "enemy_of")),
        frozenset(("canon_to", "non_canon_to")),
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _normalize_edges(
        cls,
        global_knowledge: dict[str, Any],
    ) -> list[dict[str, Any]]:
        edges = []
        graph = global_knowledge.get("graph") or {}

        for item in graph.get("edges") or []:
            if not isinstance(item, dict):
                continue

            relation = cls._norm(
                item.get("edge_type")
                or item.get("relation_type")
            ).casefold()
            source = cls._norm(
                item.get("source_node_key")
                or item.get("subject_node_key")
            )
            target = cls._norm(
                item.get("target_node_key")
                or item.get("object_node_key")
            )

            if not relation or not source or not target:
                continue

            edges.append({
                "relation_type": relation,
                "source_node_key": source,
                "target_node_key": target,
                "confidence": item.get("confidence"),
                "valid_from": item.get("valid_from"),
                "valid_to": item.get("valid_to"),
                "origin": item.get("origin")
                or item.get("origins"),
            })

        return edges

    @classmethod
    def _edge_index(
        cls,
        edges: list[dict[str, Any]],
    ) -> set[tuple[str, str, str]]:
        return {
            (
                edge["relation_type"],
                edge["source_node_key"],
                edge["target_node_key"],
            )
            for edge in edges
        }

    @classmethod
    def _check_inverse_relations(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        index = cls._edge_index(edges)
        missing = []

        for edge in edges:
            inverse = cls.INVERSE_RELATIONS.get(
                edge["relation_type"]
            )
            if not inverse:
                continue

            expected = (
                inverse,
                edge["target_node_key"],
                edge["source_node_key"],
            )
            if expected in index:
                continue

            missing.append({
                "relation_type": edge["relation_type"],
                "source_node_key": edge["source_node_key"],
                "target_node_key": edge["target_node_key"],
                "expected_inverse_relation": inverse,
                "expected_source_node_key": edge[
                    "target_node_key"
                ],
                "expected_target_node_key": edge[
                    "source_node_key"
                ],
                "severity": "warning",
                "automatic_fix": False,
                "requires_confirmation": True,
            })

        return missing

    @classmethod
    def _check_symmetric_relations(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        index = cls._edge_index(edges)
        missing = []

        for edge in edges:
            if edge["relation_type"] not in cls.SYMMETRIC_RELATIONS:
                continue

            expected = (
                edge["relation_type"],
                edge["target_node_key"],
                edge["source_node_key"],
            )
            if expected in index:
                continue

            missing.append({
                "relation_type": edge["relation_type"],
                "source_node_key": edge["source_node_key"],
                "target_node_key": edge["target_node_key"],
                "expected_reverse_relation": edge[
                    "relation_type"
                ],
                "expected_source_node_key": edge[
                    "target_node_key"
                ],
                "expected_target_node_key": edge[
                    "source_node_key"
                ],
                "severity": "warning",
                "automatic_fix": False,
                "requires_confirmation": True,
            })

        return missing

    @classmethod
    def _check_contradictions(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_direction = defaultdict(set)

        for edge in edges:
            key = (
                edge["source_node_key"],
                edge["target_node_key"],
            )
            by_direction[key].add(edge["relation_type"])

        contradictions = []

        for node_pair, relations in sorted(by_direction.items()):
            for pair in cls.CONTRADICTORY_PAIRS:
                if pair.issubset(relations):
                    contradictions.append({
                        "source_node_key": node_pair[0],
                        "target_node_key": node_pair[1],
                        "relations": sorted(pair),
                        "severity": "error",
                        "automatic_fix": False,
                        "requires_confirmation": True,
                    })

        return contradictions

    @classmethod
    def _check_exclusive_relations(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped = defaultdict(set)

        for edge in edges:
            relation = edge["relation_type"]
            if relation not in cls.EXCLUSIVE_RELATIONS:
                continue

            grouped[
                (relation, edge["source_node_key"])
            ].add(edge["target_node_key"])

        conflicts = []

        for (relation, source), targets in sorted(grouped.items()):
            if len(targets) <= 1:
                continue

            conflicts.append({
                "relation_type": relation,
                "source_node_key": source,
                "target_node_keys": sorted(targets),
                "severity": "warning",
                "reason": "multiple_exclusive_targets",
                "automatic_fix": False,
                "requires_confirmation": True,
            })

        return conflicts

    @classmethod
    def _check_direct_self_conflicts(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        conflicts = []

        for edge in edges:
            relation = edge["relation_type"]
            source = edge["source_node_key"]
            target = edge["target_node_key"]

            if source != target:
                continue

            if (
                relation in cls.SYMMETRIC_RELATIONS
                or relation in cls.INVERSE_RELATIONS
                or relation in cls.EXCLUSIVE_RELATIONS
            ):
                conflicts.append({
                    "relation_type": relation,
                    "source_node_key": source,
                    "target_node_key": target,
                    "severity": "error",
                    "reason": "invalid_self_relationship",
                    "automatic_fix": False,
                    "requires_confirmation": True,
                })

        return conflicts

    @classmethod
    def build(
        cls,
        *,
        global_knowledge: dict[str, Any],
        knowledge_graph_validation: dict[str, Any],
        missing_entity_resolution: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        edges = cls._normalize_edges(global_knowledge)

        inverse_warnings = cls._check_inverse_relations(edges)
        symmetric_warnings = cls._check_symmetric_relations(edges)
        contradictions = cls._check_contradictions(edges)
        exclusive_conflicts = cls._check_exclusive_relations(edges)
        self_conflicts = cls._check_direct_self_conflicts(edges)

        error_count = (
            len(contradictions)
            + len(self_conflicts)
        )
        warning_count = (
            len(inverse_warnings)
            + len(symmetric_warnings)
            + len(exclusive_conflicts)
        )

        if error_count:
            status = "fail"
        elif warning_count:
            status = "warn"
        else:
            status = "pass"

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "status": status,
            "checks": {
                "missing_inverse_relations": inverse_warnings,
                "missing_symmetric_relations": symmetric_warnings,
                "contradictory_relations": contradictions,
                "exclusive_relation_conflicts": exclusive_conflicts,
                "invalid_self_relationships": self_conflicts,
            },
            "summary": {
                "edge_count": len(edges),
                "missing_inverse_count": len(
                    inverse_warnings
                ),
                "missing_symmetric_count": len(
                    symmetric_warnings
                ),
                "contradiction_count": len(
                    contradictions
                ),
                "exclusive_conflict_count": len(
                    exclusive_conflicts
                ),
                "invalid_self_relationship_count": len(
                    self_conflicts
                ),
                "upstream_graph_status": (
                    knowledge_graph_validation.get("status")
                ),
                "missing_entity_proposal_count": (
                    missing_entity_resolution
                    .get("summary", {})
                    .get("missing_node_proposal_count", 0)
                ),
                "error_count": error_count,
                "warning_count": warning_count,
            },
            "automatic_fix": False,
            "automatic_import": False,
            "requires_confirmation": True,
        }
