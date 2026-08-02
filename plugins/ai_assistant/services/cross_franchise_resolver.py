from __future__ import annotations

from collections import defaultdict
from typing import Any


class CrossFranchiseResolver:
    STRATEGY = "cross_franchise_resolver_v670"

    RELATION_TYPES = {
        "belongs_to_franchise",
        "belongs_to_universe",
        "belongs_to_timeline",
        "shares_franchise",
        "shares_universe",
        "crosses_over_with",
        "backdoor_pilot_for",
        "spin_off_of",
        "soft_reboot_of",
        "hard_reboot_of",
        "parallel_universe_of",
        "alternate_timeline_of",
        "legacy_sequel_of",
        "non_canon_to",
    }

    NODE_TYPES = {
        "franchise",
        "universe",
        "timeline",
        "canon",
        "crossover_event",
        "backdoor_pilot",
        "movie",
        "series",
        "season",
        "episode",
        "special",
        "audiobook",
        "book",
        "game",
    }

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
    def _collect_nodes(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        nodes = {}
        for payload in payloads:
            strategy = cls._norm(payload.get("strategy")) or "unknown"
            candidates = (
                payload.get("nodes")
                or payload.get("entities")
                or payload.get("entity_proposals")
                or []
            )

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                node_id = cls._norm(
                    item.get("id")
                    or item.get("node_key")
                    or item.get("entity_id")
                )
                title = cls._norm(
                    item.get("title")
                    or item.get("name")
                    or item.get("label")
                )
                node_type = cls._norm(
                    item.get("node_type")
                    or item.get("entity_type")
                    or item.get("type")
                ).casefold()

                if node_type not in cls.NODE_TYPES:
                    continue

                if not node_id:
                    if not title:
                        continue
                    safe = "-".join(title.casefold().split())
                    node_id = f"{node_type}:{safe}"

                if not title:
                    title = node_id.split(":", 1)[-1]

                candidate = {
                    "id": node_id,
                    "title": title,
                    "node_type": node_type,
                    "year": item.get("year"),
                    "confidence": cls._float(
                        item.get("confidence"), 0.6
                    ),
                    "origin": strategy,
                    "requires_confirmation": True,
                }

                existing = nodes.get(node_id)
                if (
                    existing is None
                    or candidate["confidence"] > existing["confidence"]
                ):
                    nodes[node_id] = candidate

        return list(nodes.values())

    @classmethod
    def _collect_edges(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        edges = []

        for payload in payloads:
            strategy = cls._norm(payload.get("strategy")) or "unknown"
            candidates = (
                payload.get("edges")
                or payload.get("relations")
                or payload.get("relation_proposals")
                or payload.get("conclusions")
                or []
            )

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                edge_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                ).casefold()

                if edge_type not in cls.RELATION_TYPES:
                    continue

                source = cls._norm(
                    item.get("source_node_key")
                    or item.get("source_id")
                    or item.get("subject_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("target_id")
                    or item.get("object_node_key")
                )

                if not source or not target:
                    continue

                edges.append({
                    "edge_type": edge_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "confidence": cls._float(
                        item.get("confidence"), 0.6
                    ),
                    "origin": strategy,
                    "reason": cls._norm(
                        item.get("reason")
                        or item.get("sentence")
                    ),
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                })

        return edges

    @classmethod
    def _deduplicate_edges(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unique = {}

        for edge in edges:
            key = (
                edge["edge_type"],
                edge["source_node_key"],
                edge["target_node_key"],
            )
            existing = unique.get(key)
            if existing is None or edge["confidence"] > existing["confidence"]:
                unique[key] = edge

        return list(unique.values())

    @classmethod
    def _build_boundaries(
        cls,
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        memberships = defaultdict(lambda: {
            "franchises": set(),
            "universes": set(),
            "timelines": set(),
        })

        for edge in edges:
            source = edge["source_node_key"]
            target = edge["target_node_key"]
            edge_type = edge["edge_type"]

            if edge_type == "belongs_to_franchise":
                memberships[source]["franchises"].add(target)
            elif edge_type == "belongs_to_universe":
                memberships[source]["universes"].add(target)
            elif edge_type == "belongs_to_timeline":
                memberships[source]["timelines"].add(target)

        boundaries = []
        for node_key, values in sorted(memberships.items()):
            if (
                len(values["franchises"]) > 1
                or len(values["universes"]) > 1
                or len(values["timelines"]) > 1
            ):
                boundaries.append({
                    "node_key": node_key,
                    "franchises": sorted(values["franchises"]),
                    "universes": sorted(values["universes"]),
                    "timelines": sorted(values["timelines"]),
                    "status": "ambiguous_boundary",
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                })

        return boundaries

    @classmethod
    def build(
        cls,
        *,
        franchise_knowledge_graph: dict[str, Any],
        entity_resolution_graph: dict[str, Any],
        canonical_conflicts: dict[str, Any],
        story_arc_linking: dict[str, Any],
        semantic_result: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nodes = cls._collect_nodes(
            franchise_knowledge_graph,
            entity_resolution_graph,
            semantic_result,
        )

        edges = cls._deduplicate_edges(
            cls._collect_edges(
                franchise_knowledge_graph,
                entity_resolution_graph,
                story_arc_linking,
                semantic_result,
            )
        )

        boundaries = cls._build_boundaries(edges)

        relation_counts = defaultdict(int)
        for edge in edges:
            relation_counts[edge["edge_type"]] += 1

        node_counts = defaultdict(int)
        for node in nodes:
            node_counts[node["node_type"]] += 1

        crossovers = [
            edge for edge in edges
            if edge["edge_type"] == "crosses_over_with"
        ]
        backdoor_pilots = [
            edge for edge in edges
            if edge["edge_type"] == "backdoor_pilot_for"
        ]
        reboots = [
            edge for edge in edges
            if edge["edge_type"] in {
                "soft_reboot_of",
                "hard_reboot_of",
                "legacy_sequel_of",
            }
        ]

        conflict_count = len(
            canonical_conflicts.get("conflicts") or []
        )
        overall_confidence = (
            round(
                sum(edge["confidence"] for edge in edges)
                / len(edges),
                4,
            )
            if edges else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "nodes": nodes,
            "edges": edges,
            "crossovers": crossovers,
            "backdoor_pilots": backdoor_pilots,
            "reboots": reboots,
            "canonical_boundaries": boundaries,
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "franchise_count": node_counts.get("franchise", 0),
                "universe_count": node_counts.get("universe", 0),
                "timeline_count": node_counts.get("timeline", 0),
                "crossover_count": len(crossovers),
                "backdoor_pilot_count": len(backdoor_pilots),
                "reboot_count": len(reboots),
                "ambiguous_boundary_count": len(boundaries),
                "upstream_conflict_count": conflict_count,
                "relation_counts": dict(sorted(relation_counts.items())),
                "node_type_counts": dict(sorted(node_counts.items())),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if edges or boundaries or conflict_count
                    else "no_cross_franchise_relations"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
