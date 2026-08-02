from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class KnowledgeGraphValidator:
    STRATEGY = "knowledge_graph_validator_v702"

    DAG_RELATIONS = {
        "parent_of",
        "prequel_of",
        "sequel_of",
        "spin_off_of",
        "belongs_to_franchise",
        "belongs_to_universe",
        "belongs_to_timeline",
        "backdoor_pilot_for",
        "legacy_sequel_of",
        "soft_reboot_of",
        "hard_reboot_of",
    }

    NO_SELF_RELATIONS = {
        "parent_of",
        "child_of",
        "sibling_of",
        "married_to",
        "partner_of",
        "enemy_of",
        "ally_of",
        "prequel_of",
        "sequel_of",
        "spin_off_of",
        "belongs_to_franchise",
        "belongs_to_universe",
        "belongs_to_timeline",
        "backdoor_pilot_for",
        "legacy_sequel_of",
        "soft_reboot_of",
        "hard_reboot_of",
        "parallel_universe_of",
        "alternate_timeline_of",
        "non_canon_to",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _validate_nodes(
        cls,
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        node_keys = []
        missing_keys = []
        invalid_types = []

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                missing_keys.append(f"index:{index}")
                continue

            node_key = cls._norm(
                node.get("node_key")
                or node.get("id")
            )
            if not node_key:
                missing_keys.append(f"index:{index}")
                continue

            node_keys.append(node_key)

            node_type = cls._norm(
                node.get("node_type")
                or node.get("entity_type")
                or node.get("type")
            )
            if not node_type:
                invalid_types.append(node_key)

        duplicates = sorted(
            key for key, count in Counter(node_keys).items()
            if count > 1
        )

        return {
            "node_count": len(nodes),
            "unique_node_count": len(set(node_keys)),
            "duplicate_node_keys": duplicates,
            "missing_node_keys": missing_keys,
            "nodes_without_type": invalid_types,
            "status": (
                "ok"
                if not duplicates
                and not missing_keys
                and not invalid_types
                else "error"
            ),
        }

    @classmethod
    def _validate_edges(
        cls,
        edges: list[dict[str, Any]],
        known_nodes: set[str],
    ) -> dict[str, Any]:
        edge_keys = []
        missing_fields = []
        orphaned_edges = []
        self_relations = []

        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                missing_fields.append(f"index:{index}")
                continue

            edge_type = cls._norm(
                edge.get("edge_type")
                or edge.get("relation_type")
            ).casefold()
            source = cls._norm(
                edge.get("source_node_key")
                or edge.get("subject_node_key")
            )
            target = cls._norm(
                edge.get("target_node_key")
                or edge.get("object_node_key")
            )

            if not edge_type or not source or not target:
                missing_fields.append(f"index:{index}")
                continue

            edge_key = f"{edge_type}|{source}|{target}"
            edge_keys.append(edge_key)

            missing_refs = []
            if source not in known_nodes:
                missing_refs.append(source)
            if target not in known_nodes:
                missing_refs.append(target)
            if missing_refs:
                orphaned_edges.append({
                    "edge_key": edge_key,
                    "missing_nodes": sorted(set(missing_refs)),
                })

            if source == target and edge_type in cls.NO_SELF_RELATIONS:
                self_relations.append(edge_key)

        duplicates = sorted(
            key for key, count in Counter(edge_keys).items()
            if count > 1
        )

        return {
            "edge_count": len(edges),
            "unique_edge_count": len(set(edge_keys)),
            "duplicate_edge_keys": duplicates,
            "missing_edge_fields": missing_fields,
            "orphaned_edges": orphaned_edges,
            "invalid_self_relations": sorted(self_relations),
            "status": (
                "ok"
                if not duplicates
                and not missing_fields
                and not orphaned_edges
                and not self_relations
                else "error"
            ),
        }

    @classmethod
    def _find_cycles(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_type = defaultdict(lambda: defaultdict(list))

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_type = cls._norm(
                edge.get("edge_type")
                or edge.get("relation_type")
            ).casefold()
            source = cls._norm(
                edge.get("source_node_key")
                or edge.get("subject_node_key")
            )
            target = cls._norm(
                edge.get("target_node_key")
                or edge.get("object_node_key")
            )
            if (
                edge_type in cls.DAG_RELATIONS
                and source
                and target
            ):
                by_type[edge_type][source].append(target)

        cycles = []

        for edge_type, graph in sorted(by_type.items()):
            visited = set()
            active = set()
            stack = []

            def visit(node: str) -> None:
                if node in active:
                    try:
                        start = stack.index(node)
                    except ValueError:
                        start = 0
                    cycle_nodes = stack[start:] + [node]
                    cycle_key = " -> ".join(cycle_nodes)
                    record = {
                        "edge_type": edge_type,
                        "cycle": cycle_nodes,
                        "cycle_key": cycle_key,
                    }
                    if record not in cycles:
                        cycles.append(record)
                    return

                if node in visited:
                    return

                visited.add(node)
                active.add(node)
                stack.append(node)

                for target in graph.get(node, []):
                    visit(target)

                stack.pop()
                active.remove(node)

            for node in list(graph):
                visit(node)

        return cycles

    @classmethod
    def _validate_semantics(
        cls,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        node_types = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            key = cls._norm(node.get("node_key") or node.get("id"))
            node_type = cls._norm(
                node.get("node_type")
                or node.get("entity_type")
                or node.get("type")
            ).casefold()
            if key:
                node_types[key] = node_type

        type_errors = []

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_type = cls._norm(
                edge.get("edge_type")
                or edge.get("relation_type")
            ).casefold()
            source = cls._norm(
                edge.get("source_node_key")
                or edge.get("subject_node_key")
            )
            target = cls._norm(
                edge.get("target_node_key")
                or edge.get("object_node_key")
            )

            target_type = node_types.get(target, "")

            expected_target = {
                "belongs_to_franchise": "franchise",
                "belongs_to_universe": "universe",
                "belongs_to_timeline": "timeline",
            }.get(edge_type)

            if (
                expected_target
                and target_type
                and target_type != expected_target
            ):
                type_errors.append({
                    "edge_type": edge_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "expected_target_type": expected_target,
                    "actual_target_type": target_type,
                })

        return {
            "type_constraint_errors": type_errors,
            "status": "ok" if not type_errors else "warning",
        }

    @classmethod
    def build(
        cls,
        *,
        global_knowledge: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        graph = global_knowledge.get("graph") or {}
        nodes = list(graph.get("nodes") or [])
        edges = list(graph.get("edges") or [])

        node_check = cls._validate_nodes(nodes)
        known_nodes = {
            cls._norm(node.get("node_key") or node.get("id"))
            for node in nodes
            if isinstance(node, dict)
            and cls._norm(node.get("node_key") or node.get("id"))
        }
        edge_check = cls._validate_edges(edges, known_nodes)
        cycles = cls._find_cycles(edges)
        semantics = cls._validate_semantics(nodes, edges)

        errors = []
        warnings = []

        if node_check["status"] != "ok":
            errors.append("node_validation_failed")
        if edge_check["status"] != "ok":
            errors.append("edge_validation_failed")
        if cycles:
            errors.append("disallowed_cycles_detected")
        if semantics["status"] != "ok":
            warnings.append("semantic_type_constraints_warning")

        if errors:
            status = "fail"
        elif warnings:
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
                "nodes": node_check,
                "edges": edge_check,
                "cycles": {
                    "cycle_count": len(cycles),
                    "cycles": cycles,
                    "status": "ok" if not cycles else "error",
                },
                "semantics": semantics,
            },
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "duplicate_node_count": len(
                    node_check["duplicate_node_keys"]
                ),
                "duplicate_edge_count": len(
                    edge_check["duplicate_edge_keys"]
                ),
                "orphaned_edge_count": len(
                    edge_check["orphaned_edges"]
                ),
                "invalid_self_relation_count": len(
                    edge_check["invalid_self_relations"]
                ),
                "cycle_count": len(cycles),
                "semantic_warning_count": len(
                    semantics["type_constraint_errors"]
                ),
                "error_count": len(errors),
                "warning_count": len(warnings),
            },
            "errors": errors,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
