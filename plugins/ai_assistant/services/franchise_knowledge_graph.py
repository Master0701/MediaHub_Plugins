from __future__ import annotations

from collections import defaultdict
from typing import Any


class FranchiseKnowledgeGraph:
    STRATEGY = "franchise_knowledge_graph_v590"

    MEDIA_RELATIONS = {
        "sequel",
        "prequel",
        "spin_off",
        "spinoff",
        "crossover",
        "reboot",
        "remake",
        "backdoor_pilot",
        "part_of",
        "installment_of",
        "belongs_to_universe",
        "same_universe",
    }

    CANON_RELATIONS = {
        "canon",
        "non_canon",
        "alternate_timeline",
        "timeline_branch",
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
    def _node(
        cls,
        node_id: str,
        node_type: str,
        title: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        item = {
            "id": node_id,
            "node_type": node_type,
            "title": title or node_id,
        }
        item.update(extra)
        return item

    @classmethod
    def _collect_semantic_edges(
        cls,
        semantic_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        edges = []
        primary = cls._norm(semantic_result.get("primary_title"))
        primary_id = (
            "media:" + primary.casefold().replace(" ", "-")
            if primary
            else "media:unknown"
        )

        for proposal in semantic_result.get("relation_proposals") or []:
            if not isinstance(proposal, dict):
                continue
            relation_type = cls._norm(
                proposal.get("relation_type")
            ).casefold()
            if relation_type not in cls.MEDIA_RELATIONS:
                continue

            sentence = cls._norm(proposal.get("sentence"))
            target = cls._norm(proposal.get("target_title"))
            target_id = (
                "media:" + target.casefold().replace(" ", "-")
                if target
                else f"proposal:{proposal.get('id') or len(edges)}"
            )
            edges.append({
                "edge_type": relation_type,
                "source_node_key": primary_id,
                "target_node_key": target_id,
                "confidence": cls._confidence(
                    proposal.get("confidence")
                ),
                "reason": proposal.get("reason"),
                "sentence": sentence,
                "origin": "semantic_result",
                "requires_confirmation": True,
            })
        return edges

    @classmethod
    def _collect_relationship_edges(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        edges = []
        for payload in payloads:
            for item in (
                payload.get("conclusions")
                or payload.get("relations")
                or payload.get("arcs")
                or []
            ):
                if not isinstance(item, dict):
                    continue
                edge_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                    or item.get("arc_type")
                ).casefold()
                source = cls._norm(
                    item.get("source_node_key")
                    or item.get("owner_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("end_node_key")
                )
                if not edge_type or not source or not target:
                    continue
                if (
                    edge_type not in cls.MEDIA_RELATIONS
                    and edge_type not in cls.CANON_RELATIONS
                    and not edge_type.endswith("_arc")
                    and edge_type != "linked_story_arc_chain"
                ):
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
    def build(
        cls,
        *,
        semantic_result: dict[str, Any],
        semantic_reasoning: dict[str, Any],
        temporal_causal_intelligence: dict[str, Any],
        narrative_intelligence: dict[str, Any],
        story_arc_linking: dict[str, Any],
        story_timeline: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        primary_title = cls._norm(
            semantic_result.get("primary_title")
        )
        primary_type = cls._norm(
            semantic_result.get("primary_entity_type")
        ) or "media"
        primary_id = (
            "media:" + primary_title.casefold().replace(" ", "-")
            if primary_title
            else "media:unknown"
        )

        nodes: dict[str, dict[str, Any]] = {
            primary_id: cls._node(
                primary_id,
                primary_type,
                primary_title or "Unbekanntes Medium",
            )
        }

        metadata = (
            semantic_result.get("metadata")
            or semantic_result.get("fields", {}).get("metadata")
            or {}
        )
        universe = cls._norm(metadata.get("universe"))
        franchise = cls._norm(metadata.get("franchise"))

        if universe:
            universe_id = (
                "universe:" + universe.casefold().replace(" ", "-")
            )
            nodes[universe_id] = cls._node(
                universe_id,
                "universe",
                universe,
            )
        else:
            universe_id = None

        if franchise:
            franchise_id = (
                "franchise:" + franchise.casefold().replace(" ", "-")
            )
            nodes[franchise_id] = cls._node(
                franchise_id,
                "franchise",
                franchise,
            )
        else:
            franchise_id = None

        edges = cls._collect_semantic_edges(semantic_result)
        edges += cls._collect_relationship_edges(
            semantic_reasoning,
            temporal_causal_intelligence,
            narrative_intelligence,
            story_arc_linking,
            story_timeline,
        )

        if universe_id:
            edges.append({
                "edge_type": "belongs_to_universe",
                "source_node_key": primary_id,
                "target_node_key": universe_id,
                "confidence": 0.9,
                "origin": "semantic_metadata",
                "requires_confirmation": True,
            })

        if franchise_id:
            edges.append({
                "edge_type": "installment_of",
                "source_node_key": primary_id,
                "target_node_key": franchise_id,
                "confidence": 0.9,
                "origin": "semantic_metadata",
                "requires_confirmation": True,
            })

        for edge in edges:
            for key in (
                edge["source_node_key"],
                edge["target_node_key"],
            ):
                if key not in nodes:
                    if key.startswith("universe:"):
                        node_type = "universe"
                    elif key.startswith("franchise:"):
                        node_type = "franchise"
                    elif key.startswith("character:"):
                        node_type = "character"
                    elif key.startswith("event:"):
                        node_type = "event"
                    elif key.startswith("timeline:"):
                        node_type = "timeline"
                    else:
                        node_type = "media_or_narrative"
                    nodes[key] = cls._node(
                        key,
                        node_type,
                        key.split(":", 1)[-1],
                    )

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

        grouped = defaultdict(int)
        for edge in unique_edges:
            grouped[edge["edge_type"]] += 1

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
            "primary_node_key": primary_id,
            "nodes": list(nodes.values()),
            "edges": unique_edges,
            "relation_counts": dict(sorted(grouped.items())),
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(unique_edges),
                "franchise_node_count": sum(
                    node["node_type"] == "franchise"
                    for node in nodes.values()
                ),
                "universe_node_count": sum(
                    node["node_type"] == "universe"
                    for node in nodes.values()
                ),
                "canon_edge_count": sum(
                    edge["edge_type"] in cls.CANON_RELATIONS
                    for edge in unique_edges
                ),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if unique_edges
                    else "no_graph_relations"
                ),
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
