from __future__ import annotations

from collections import defaultdict
from typing import Any


class CanonicalConflictResolver:
    STRATEGY = "canonical_conflict_resolver_v660"

    SOURCE_WEIGHTS = {
        "manual_confirmation": 1.0,
        "official_source": 0.95,
        "wikidata": 0.9,
        "tmdb": 0.88,
        "wikipedia": 0.82,
        "entity_resolution_graph_v610": 0.84,
        "relationship_confidence_engine_v620": 0.84,
        "character_timeline_engine_v630": 0.82,
        "character_evolution_engine_v640": 0.82,
        "character_memory_engine_v650": 0.8,
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
    def _collect_claims(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        claims = []

        for payload in payloads:
            strategy = cls._norm(payload.get("strategy")) or "unknown"

            candidates = []
            for key in (
                "claims",
                "conflicts",
                "assessments",
                "merge_proposals",
                "identity_link_proposals",
                "events",
                "changes",
                "relations",
                "edges",
            ):
                values = payload.get(key) or []
                if isinstance(values, list):
                    candidates.extend(values)

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                subject = cls._norm(
                    item.get("subject_node_key")
                    or item.get("source_node_key")
                    or item.get("left_node_key")
                    or item.get("character_node_key")
                )
                predicate = cls._norm(
                    item.get("predicate")
                    or item.get("field")
                    or item.get("relation_type")
                    or item.get("edge_type")
                    or item.get("event_type")
                    or item.get("evolution_type")
                    or item.get("proposal_type")
                    or item.get("conflict_type")
                ).casefold()
                value = item.get("value")
                if value is None:
                    value = (
                        item.get("target_node_key")
                        or item.get("right_node_key")
                        or item.get("to_value")
                        or item.get("canonical_title")
                        or item.get("year")
                    )

                if not subject or not predicate or value in (None, ""):
                    continue

                claims.append({
                    "subject_node_key": subject,
                    "predicate": predicate,
                    "value": value,
                    "value_key": cls._norm(value).casefold(),
                    "confidence": cls._float(
                        item.get("confidence"), 0.6
                    ),
                    "source": cls._norm(
                        item.get("origin")
                        or item.get("source")
                        or strategy
                    ) or "unknown",
                    "manual_confirmation": bool(
                        item.get("manual_confirmation")
                        or item.get("confirmed")
                    ),
                    "evidence": cls._norm(
                        item.get("sentence")
                        or item.get("reason")
                        or item.get("evidence")
                    ),
                    "requires_confirmation": True,
                })

        return claims

    @classmethod
    def _score_claim(cls, claim: dict[str, Any]) -> float:
        source_weight = cls._source_weight(claim["source"])
        manual_bonus = 0.12 if claim["manual_confirmation"] else 0.0
        score = (
            claim["confidence"] * 0.65
            + source_weight * 0.35
            + manual_bonus
        )
        return round(max(0.0, min(1.0, score)), 4)

    @classmethod
    def _group_conflicts(
        cls,
        claims: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped = defaultdict(list)
        for claim in claims:
            grouped[
                (
                    claim["subject_node_key"],
                    claim["predicate"],
                )
            ].append(claim)

        conflicts = []
        for (subject, predicate), group in grouped.items():
            values = defaultdict(list)
            for claim in group:
                values[claim["value_key"]].append(claim)

            if len(values) <= 1:
                continue

            candidates = []
            for value_key, value_claims in values.items():
                best = max(
                    value_claims,
                    key=cls._score_claim,
                )
                candidates.append({
                    "value": best["value"],
                    "value_key": value_key,
                    "score": cls._score_claim(best),
                    "source_count": len({
                        claim["source"]
                        for claim in value_claims
                    }),
                    "sources": sorted({
                        claim["source"]
                        for claim in value_claims
                    }),
                    "evidence": [
                        claim["evidence"]
                        for claim in value_claims
                        if claim["evidence"]
                    ],
                    "manual_confirmation": any(
                        claim["manual_confirmation"]
                        for claim in value_claims
                    ),
                })

            candidates.sort(
                key=lambda item: (
                    -item["score"],
                    -item["source_count"],
                    item["value_key"],
                )
            )

            top = candidates[0]
            runner_up = candidates[1]
            margin = round(
                max(0.0, top["score"] - runner_up["score"]),
                4,
            )

            if top["manual_confirmation"] and top["score"] >= 0.8:
                recommendation = "prefer_confirmed_value"
            elif margin >= 0.15 and top["source_count"] >= runner_up["source_count"]:
                recommendation = "prefer_highest_scored_value"
            else:
                recommendation = "manual_review_required"

            conflicts.append({
                "conflict_id": (
                    f"{subject}:{predicate}"
                ),
                "subject_node_key": subject,
                "predicate": predicate,
                "candidates": candidates,
                "recommended_value": (
                    top["value"]
                    if recommendation != "manual_review_required"
                    else None
                ),
                "recommendation": recommendation,
                "score_margin": margin,
                "automatic_resolution": False,
                "requires_confirmation": True,
            })

        return conflicts

    @classmethod
    def build(
        cls,
        *,
        entity_resolution_graph: dict[str, Any],
        relationship_confidence: dict[str, Any],
        character_timeline: dict[str, Any],
        character_evolution: dict[str, Any],
        character_memory: dict[str, Any],
        graph_validation: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        claims = cls._collect_claims(
            entity_resolution_graph,
            relationship_confidence,
            character_timeline,
            character_evolution,
            character_memory,
            graph_validation,
        )

        conflicts = cls._group_conflicts(claims)

        recommendation_counts = defaultdict(int)
        for conflict in conflicts:
            recommendation_counts[
                conflict["recommendation"]
            ] += 1

        overall_confidence = (
            round(
                sum(
                    conflict["candidates"][0]["score"]
                    for conflict in conflicts
                    if conflict["candidates"]
                )
                / len(conflicts),
                4,
            )
            if conflicts else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "claims": claims,
            "conflicts": conflicts,
            "summary": {
                "claim_count": len(claims),
                "conflict_count": len(conflicts),
                "recommendation_counts": dict(
                    sorted(recommendation_counts.items())
                ),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if conflicts else "no_canonical_conflicts"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
