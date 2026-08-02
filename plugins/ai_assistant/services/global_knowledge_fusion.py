from __future__ import annotations

from collections import defaultdict
from typing import Any


class GlobalKnowledgeFusion:
    STRATEGY = "global_knowledge_fusion_v690"

    NODE_SOURCE_KEYS = (
        "nodes",
        "entities",
        "entity_proposals",
        "profiles",
        "evolutions",
        "timelines",
    )

    EDGE_SOURCE_KEYS = (
        "edges",
        "relations",
        "relation_proposals",
        "assessments",
        "links",
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _float(cls, value: Any, default: float = 0.5) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number > 1.0:
            number /= 100.0
        return max(0.0, min(1.0, number))

    @classmethod
    def _node_key(
        cls,
        item: dict[str, Any],
        fallback_type: str = "entity",
    ) -> str:
        direct = cls._norm(
            item.get("node_key")
            or item.get("id")
            or item.get("entity_id")
            or item.get("character_node_key")
        )
        if direct:
            return direct

        node_type = cls._norm(
            item.get("node_type")
            or item.get("entity_type")
            or item.get("type")
            or fallback_type
        ).casefold() or fallback_type
        title = cls._norm(
            item.get("title")
            or item.get("name")
            or item.get("label")
        )
        if not title:
            return ""
        return f"{node_type}:{'-'.join(title.casefold().split())}"

    @classmethod
    def _collect_nodes(
        cls,
        modules: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        nodes = {}

        for module_name, payload in modules.items():
            if not isinstance(payload, dict):
                continue
            strategy = cls._norm(payload.get("strategy")) or module_name

            candidates = []
            for key in cls.NODE_SOURCE_KEYS:
                values = payload.get(key) or []
                if isinstance(values, list):
                    candidates.extend(values)

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                node_key = cls._node_key(item)
                if not node_key:
                    continue

                node_type = cls._norm(
                    item.get("node_type")
                    or item.get("entity_type")
                    or item.get("type")
                ).casefold()
                if not node_type and ":" in node_key:
                    node_type = node_key.split(":", 1)[0]
                node_type = node_type or "entity"

                title = cls._norm(
                    item.get("title")
                    or item.get("name")
                    or item.get("label")
                )
                if not title:
                    title = node_key.split(":", 1)[-1]

                confidence = cls._float(
                    item.get("confidence")
                    or item.get("overall_confidence"),
                    0.6,
                )

                candidate = {
                    "node_key": node_key,
                    "node_type": node_type,
                    "title": title,
                    "year": item.get("year"),
                    "confidence": confidence,
                    "origins": [strategy],
                    "attributes": {
                        key: value
                        for key, value in item.items()
                        if key not in {
                            "id",
                            "node_key",
                            "entity_id",
                            "character_node_key",
                            "node_type",
                            "entity_type",
                            "type",
                            "title",
                            "name",
                            "label",
                            "confidence",
                            "overall_confidence",
                        }
                    },
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                }

                existing = nodes.get(node_key)
                if existing is None:
                    nodes[node_key] = candidate
                    continue

                existing["origins"] = sorted(set(
                    existing["origins"] + candidate["origins"]
                ))
                if candidate["confidence"] > existing["confidence"]:
                    existing["confidence"] = candidate["confidence"]
                if not existing.get("year") and candidate.get("year"):
                    existing["year"] = candidate["year"]
                existing["attributes"].update(
                    candidate.get("attributes") or {}
                )

        return list(nodes.values())

    @classmethod
    def _collect_edges(
        cls,
        modules: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        edges = {}

        for module_name, payload in modules.items():
            if not isinstance(payload, dict):
                continue
            strategy = cls._norm(payload.get("strategy")) or module_name

            candidates = []
            for key in cls.EDGE_SOURCE_KEYS:
                values = payload.get(key) or []
                if isinstance(values, list):
                    candidates.extend(values)

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                edge_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                    or item.get("predicate")
                ).casefold()
                source = cls._norm(
                    item.get("source_node_key")
                    or item.get("subject_node_key")
                    or item.get("left_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("object_node_key")
                    or item.get("right_node_key")
                    or item.get("value")
                )

                if not edge_type or not source or not target:
                    continue

                confidence = cls._float(
                    item.get("confidence")
                    or item.get("canonical_score"),
                    0.6,
                )

                key = (edge_type, source, target)
                candidate = {
                    "edge_type": edge_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "confidence": confidence,
                    "origins": [strategy],
                    "evidence": [
                        cls._norm(item.get("reason")
                        or item.get("sentence")
                        or item.get("evidence"))
                    ] if cls._norm(
                        item.get("reason")
                        or item.get("sentence")
                        or item.get("evidence")
                    ) else [],
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                }

                existing = edges.get(key)
                if existing is None:
                    edges[key] = candidate
                    continue

                existing["origins"] = sorted(set(
                    existing["origins"] + candidate["origins"]
                ))
                existing["evidence"] = sorted(set(
                    existing["evidence"] + candidate["evidence"]
                ))
                if candidate["confidence"] > existing["confidence"]:
                    existing["confidence"] = candidate["confidence"]

        return list(edges.values())

    @classmethod
    def _decision_index(
        cls,
        canonical_decisions: dict[str, Any],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        index = {}
        for decision in canonical_decisions.get("decisions") or []:
            if not isinstance(decision, dict):
                continue
            subject = cls._norm(
                decision.get("subject_node_key")
            )
            predicate = cls._norm(
                decision.get("predicate")
            ).casefold()
            if subject and predicate:
                index[(subject, predicate)] = decision
        return index

    @classmethod
    def _apply_decisions(
        cls,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        canonical_decisions: dict[str, Any],
    ) -> dict[str, Any]:
        index = cls._decision_index(canonical_decisions)
        proposed_updates = []

        for node in nodes:
            for (subject, predicate), decision in index.items():
                if subject != node["node_key"]:
                    continue
                recommended = decision.get("recommended_value")
                if recommended in (None, ""):
                    continue
                proposed_updates.append({
                    "target_type": "node",
                    "target_key": node["node_key"],
                    "field": predicate,
                    "recommended_value": recommended,
                    "confidence": cls._float(
                        decision.get("confidence"), 0.5
                    ),
                    "decision_type": decision.get(
                        "decision_type"
                    ),
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                })

        for edge in edges:
            decision = index.get((
                edge["source_node_key"],
                edge["edge_type"],
            ))
            if not decision:
                continue
            recommended = cls._norm(
                decision.get("recommended_value")
            )
            if not recommended:
                continue
            proposed_updates.append({
                "target_type": "edge",
                "target_key": (
                    f'{edge["source_node_key"]}|'
                    f'{edge["edge_type"]}|'
                    f'{edge["target_node_key"]}'
                ),
                "field": "target_node_key",
                "recommended_value": recommended,
                "confidence": cls._float(
                    decision.get("confidence"), 0.5
                ),
                "decision_type": decision.get("decision_type"),
                "automatic_resolution": False,
                "requires_confirmation": True,
            })

        return {
            "proposed_updates": proposed_updates,
            "applied_update_count": 0,
            "automatic_resolution": False,
            "requires_confirmation": True,
        }

    @classmethod
    def build(
        cls,
        *,
        semantic_result: dict[str, Any],
        entity_resolution_graph: dict[str, Any],
        relationship_confidence: dict[str, Any],
        character_relationship_graph: dict[str, Any],
        character_timeline: dict[str, Any],
        character_evolution: dict[str, Any],
        character_memory: dict[str, Any],
        franchise_knowledge_graph: dict[str, Any],
        cross_franchise: dict[str, Any],
        canonical_conflicts: dict[str, Any],
        canonical_decisions: dict[str, Any],
        graph_validation: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        modules = {
            "semantic_result": semantic_result,
            "entity_resolution_graph": entity_resolution_graph,
            "relationship_confidence": relationship_confidence,
            "character_relationship_graph": (
                character_relationship_graph
            ),
            "character_timeline": character_timeline,
            "character_evolution": character_evolution,
            "character_memory": character_memory,
            "franchise_knowledge_graph": franchise_knowledge_graph,
            "cross_franchise": cross_franchise,
        }

        nodes = cls._collect_nodes(modules)
        edges = cls._collect_edges(modules)

        fusion_plan = cls._apply_decisions(
            nodes,
            edges,
            canonical_decisions,
        )

        node_type_counts = defaultdict(int)
        for node in nodes:
            node_type_counts[node["node_type"]] += 1

        edge_type_counts = defaultdict(int)
        for edge in edges:
            edge_type_counts[edge["edge_type"]] += 1

        unresolved_conflict_count = (
            len(canonical_conflicts.get("conflicts") or [])
            + len(graph_validation.get("conflicts") or [])
        )
        overall_confidence = (
            round(
                (
                    sum(node["confidence"] for node in nodes)
                    + sum(edge["confidence"] for edge in edges)
                )
                / max(1, len(nodes) + len(edges)),
                4,
            )
            if nodes or edges else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "graph": {
                "nodes": sorted(
                    nodes,
                    key=lambda item: (
                        item["node_type"],
                        item["node_key"],
                    ),
                ),
                "edges": sorted(
                    edges,
                    key=lambda item: (
                        item["edge_type"],
                        item["source_node_key"],
                        item["target_node_key"],
                    ),
                ),
            },
            "fusion_plan": fusion_plan,
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_type_counts": dict(
                    sorted(node_type_counts.items())
                ),
                "edge_type_counts": dict(
                    sorted(edge_type_counts.items())
                ),
                "proposed_update_count": len(
                    fusion_plan["proposed_updates"]
                ),
                "unresolved_conflict_count": (
                    unresolved_conflict_count
                ),
                "canonical_decision_count": len(
                    canonical_decisions.get("decisions") or []
                ),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if nodes or edges or unresolved_conflict_count
                    else "no_knowledge_to_fuse"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
