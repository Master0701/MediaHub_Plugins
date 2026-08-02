from __future__ import annotations

from collections import defaultdict
from typing import Any


class RelationshipConfidenceEngine:
    STRATEGY = "relationship_confidence_engine_v620"

    SOURCE_WEIGHTS = {
        "manual_confirmation": 1.0,
        "official_source": 0.95,
        "wikidata": 0.9,
        "tmdb": 0.88,
        "wikipedia": 0.82,
        "semantic_result": 0.75,
        "character_relationship_engine_v413": 0.76,
        "character_relationship_graph_v600": 0.8,
        "franchise_knowledge_graph_v590": 0.8,
        "entity_resolution_graph_v610": 0.84,
        "unknown": 0.55,
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
    def _source_weight(cls, source: Any) -> float:
        key = cls._norm(source).casefold()
        if not key:
            return cls.SOURCE_WEIGHTS["unknown"]
        if key in cls.SOURCE_WEIGHTS:
            return cls.SOURCE_WEIGHTS[key]
        for known, weight in cls.SOURCE_WEIGHTS.items():
            if known != "unknown" and known in key:
                return weight
        return cls.SOURCE_WEIGHTS["unknown"]

    @classmethod
    def confidence_level(cls, confidence: Any) -> str:
        value = cls._float(confidence, 0.0)
        if value >= 0.9:
            return "very_high"
        if value >= 0.75:
            return "high"
        if value >= 0.55:
            return "medium"
        if value >= 0.35:
            return "low"
        return "very_low"

    @classmethod
    def _collect_relationships(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relationships = []

        for payload in payloads:
            strategy = cls._norm(payload.get("strategy"))
            items = (
                payload.get("edges")
                or payload.get("relations")
                or payload.get("conclusions")
                or payload.get("merge_proposals")
                or payload.get("identity_link_proposals")
                or []
            )

            for item in items:
                if not isinstance(item, dict):
                    continue

                relation_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                    or item.get("proposal_type")
                ).casefold()
                source = cls._norm(
                    item.get("source_node_key")
                    or item.get("left_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("right_node_key")
                )

                if not relation_type or not source or not target:
                    continue

                relationships.append({
                    "relation_type": relation_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "base_confidence": cls._float(
                        item.get("confidence"), 0.5
                    ),
                    "origin": strategy or cls._norm(
                        item.get("origin")
                    ) or "unknown",
                    "reason": item.get("reason"),
                    "sentence": item.get("sentence"),
                    "manual_confirmation": bool(
                        item.get("manual_confirmation")
                        or item.get("confirmed")
                    ),
                    "requires_confirmation": bool(
                        item.get("requires_confirmation", True)
                    ),
                })

        return relationships

    @classmethod
    def _group_key(cls, item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            item["relation_type"],
            item["source_node_key"],
            item["target_node_key"],
        )

    @classmethod
    def _score_group(
        cls,
        items: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        source_weights = [
            cls._source_weight(item["origin"])
            for item in items
        ]
        base_confidences = [
            item["base_confidence"]
            for item in items
        ]

        evidence_count = len(items)
        independent_sources = sorted({
            item["origin"] for item in items
        })

        source_score = (
            sum(source_weights) / len(source_weights)
            if source_weights else 0.0
        )
        evidence_score = min(1.0, evidence_count / 3.0)
        base_score = (
            sum(base_confidences) / len(base_confidences)
            if base_confidences else 0.0
        )

        manual_confirmation = any(
            item["manual_confirmation"] for item in items
        )

        conflict_count = len(conflicts)
        conflict_penalty = min(0.45, conflict_count * 0.15)
        confirmation_bonus = 0.12 if manual_confirmation else 0.0

        raw = (
            base_score * 0.45
            + source_score * 0.35
            + evidence_score * 0.20
            + confirmation_bonus
            - conflict_penalty
        )
        confidence = round(max(0.0, min(1.0, raw)), 4)

        if manual_confirmation and confidence >= 0.75:
            status = "confirmed"
        elif conflict_count:
            status = "conflicted"
        elif confidence >= 0.75:
            status = "high_confidence_review"
        else:
            status = "needs_review"

        return {
            "confidence": confidence,
            "confidence_level": cls.confidence_level(confidence),
            "status": status,
            "evidence_count": evidence_count,
            "independent_source_count": len(independent_sources),
            "evidence_sources": independent_sources,
            "source_score": round(source_score, 4),
            "evidence_score": round(evidence_score, 4),
            "base_score": round(base_score, 4),
            "manual_confirmation": manual_confirmation,
            "conflict_count": conflict_count,
            "automatic_resolution": False,
            "requires_confirmation": True,
        }

    @classmethod
    def build(
        cls,
        *,
        character_relationship_graph: dict[str, Any],
        franchise_knowledge_graph: dict[str, Any],
        entity_resolution_graph: dict[str, Any],
        relationship_intelligence: dict[str, Any],
        graph_validation: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relationships = cls._collect_relationships(
            character_relationship_graph,
            franchise_knowledge_graph,
            entity_resolution_graph,
            relationship_intelligence,
        )

        conflicts_by_key = defaultdict(list)
        for conflict in (
            character_relationship_graph.get("conflicts") or []
        ) + (
            graph_validation.get("conflicts") or []
        ):
            if not isinstance(conflict, dict):
                continue
            source_key = cls._norm(
                conflict.get("source_node_key")
            )
            target_key = cls._norm(
                conflict.get("target_node_key")
            )
            relation_a = cls._norm(
                conflict.get("relationship_a")
                or conflict.get("edge_type")
            ).casefold()
            relation_b = cls._norm(
                conflict.get("relationship_b")
            ).casefold()

            if relation_a and source_key and target_key:
                conflicts_by_key[
                    (relation_a, source_key, target_key)
                ].append(conflict)
            if relation_b and source_key and target_key:
                conflicts_by_key[
                    (relation_b, source_key, target_key)
                ].append(conflict)

        grouped = defaultdict(list)
        for item in relationships:
            grouped[cls._group_key(item)].append(item)

        assessments = []
        for key, items in grouped.items():
            relation_type, source_key, target_key = key
            assessment = cls._score_group(
                items,
                conflicts_by_key.get(key, []),
            )
            assessments.append({
                "relation_type": relation_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                **assessment,
            })

        assessments.sort(
            key=lambda item: (
                -item["confidence"],
                item["relation_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
        )

        level_counts = defaultdict(int)
        status_counts = defaultdict(int)
        for item in assessments:
            level_counts[item["confidence_level"]] += 1
            status_counts[item["status"]] += 1

        overall_confidence = (
            round(
                sum(item["confidence"] for item in assessments)
                / len(assessments),
                4,
            )
            if assessments else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "assessments": assessments,
            "summary": {
                "relationship_count": len(assessments),
                "overall_confidence": overall_confidence,
                "confidence_levels": dict(sorted(level_counts.items())),
                "statuses": dict(sorted(status_counts.items())),
                "confirmed_count": status_counts.get("confirmed", 0),
                "conflicted_count": status_counts.get("conflicted", 0),
                "needs_review_count": (
                    status_counts.get("needs_review", 0)
                    + status_counts.get(
                        "high_confidence_review", 0
                    )
                ),
            },
            "decision": {
                "status": (
                    "needs_review"
                    if assessments else
                    "no_relationships"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
