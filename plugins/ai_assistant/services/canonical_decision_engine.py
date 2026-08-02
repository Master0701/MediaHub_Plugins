from __future__ import annotations

from collections import defaultdict
from typing import Any


class CanonicalDecisionEngine:
    STRATEGY = "canonical_decision_engine_v680"

    SOURCE_WEIGHTS = {
        "manual_confirmation": 1.0,
        "official_source": 0.96,
        "wikidata": 0.92,
        "tmdb": 0.89,
        "wikipedia": 0.82,
        "canonical_conflict_resolver_v660": 0.86,
        "cross_franchise_resolver_v670": 0.86,
        "relationship_confidence_engine_v620": 0.85,
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
    def _collect_candidates(
        cls,
        canonical_conflicts: dict[str, Any],
        relationship_confidence: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidates = []

        for conflict in canonical_conflicts.get("conflicts") or []:
            if not isinstance(conflict, dict):
                continue

            subject = cls._norm(conflict.get("subject_node_key"))
            predicate = cls._norm(conflict.get("predicate")).casefold()
            if not subject or not predicate:
                continue

            for item in conflict.get("candidates") or []:
                if not isinstance(item, dict):
                    continue
                candidates.append({
                    "subject_node_key": subject,
                    "predicate": predicate,
                    "value": item.get("value"),
                    "confidence": cls._float(
                        item.get("score"), 0.5
                    ),
                    "source_count": int(
                        item.get("source_count") or 1
                    ),
                    "sources": list(item.get("sources") or []),
                    "manual_confirmation": bool(
                        item.get("manual_confirmation")
                    ),
                    "evidence": list(item.get("evidence") or []),
                    "origin": canonical_conflicts.get("strategy")
                    or "unknown",
                })

        for assessment in relationship_confidence.get("assessments") or []:
            if not isinstance(assessment, dict):
                continue

            subject = cls._norm(
                assessment.get("source_node_key")
            )
            target = cls._norm(
                assessment.get("target_node_key")
            )
            predicate = cls._norm(
                assessment.get("relation_type")
            ).casefold()
            if not subject or not target or not predicate:
                continue

            candidates.append({
                "subject_node_key": subject,
                "predicate": predicate,
                "value": target,
                "confidence": cls._float(
                    assessment.get("confidence"), 0.5
                ),
                "source_count": int(
                    assessment.get("independent_source_count") or 1
                ),
                "sources": list(
                    assessment.get("evidence_sources") or []
                ),
                "manual_confirmation": bool(
                    assessment.get("manual_confirmation")
                ),
                "evidence": [],
                "origin": relationship_confidence.get("strategy")
                or "unknown",
            })

        return candidates

    @classmethod
    def _boundary_penalty(
        cls,
        candidate: dict[str, Any],
        cross_franchise: dict[str, Any],
    ) -> tuple[float, list[str]]:
        penalty = 0.0
        reasons = []

        subject = candidate["subject_node_key"]
        for boundary in cross_franchise.get(
            "canonical_boundaries"
        ) or []:
            if not isinstance(boundary, dict):
                continue
            if cls._norm(boundary.get("node_key")) != subject:
                continue

            penalty += 0.15
            reasons.append("ambiguous_franchise_or_universe_boundary")

        return min(0.3, penalty), reasons

    @classmethod
    def _conflict_penalty(
        cls,
        candidate: dict[str, Any],
        graph_validation: dict[str, Any],
    ) -> tuple[float, list[str]]:
        penalty = 0.0
        reasons = []

        subject = candidate["subject_node_key"]
        predicate = candidate["predicate"]

        for conflict in graph_validation.get("conflicts") or []:
            if not isinstance(conflict, dict):
                continue

            conflict_subject = cls._norm(
                conflict.get("source_node_key")
                or conflict.get("subject_node_key")
            )
            relation_a = cls._norm(
                conflict.get("relationship_a")
                or conflict.get("edge_type")
                or conflict.get("predicate")
            ).casefold()
            relation_b = cls._norm(
                conflict.get("relationship_b")
            ).casefold()

            if conflict_subject != subject:
                continue
            if predicate not in {relation_a, relation_b}:
                continue

            penalty += 0.15
            reasons.append("graph_conflict")

        return min(0.45, penalty), reasons

    @classmethod
    def _score_candidate(
        cls,
        candidate: dict[str, Any],
        cross_franchise: dict[str, Any],
        graph_validation: dict[str, Any],
    ) -> dict[str, Any]:
        sources = candidate["sources"] or [candidate["origin"]]
        source_score = sum(
            cls._source_weight(source) for source in sources
        ) / len(sources)

        consensus_score = min(
            1.0,
            max(1, candidate["source_count"]) / 3.0,
        )
        confirmation_bonus = (
            0.14 if candidate["manual_confirmation"] else 0.0
        )

        boundary_penalty, boundary_reasons = (
            cls._boundary_penalty(
                candidate,
                cross_franchise,
            )
        )
        conflict_penalty, conflict_reasons = (
            cls._conflict_penalty(
                candidate,
                graph_validation,
            )
        )

        raw_score = (
            candidate["confidence"] * 0.45
            + source_score * 0.3
            + consensus_score * 0.25
            + confirmation_bonus
            - boundary_penalty
            - conflict_penalty
        )
        score = round(max(0.0, min(1.0, raw_score)), 4)

        reasons = []
        if candidate["manual_confirmation"]:
            reasons.append("manual_confirmation")
        if candidate["source_count"] >= 2:
            reasons.append("multiple_independent_sources")
        if source_score >= 0.85:
            reasons.append("high_quality_sources")
        reasons.extend(boundary_reasons)
        reasons.extend(conflict_reasons)

        return {
            **candidate,
            "source_score": round(source_score, 4),
            "consensus_score": round(consensus_score, 4),
            "boundary_penalty": round(boundary_penalty, 4),
            "conflict_penalty": round(conflict_penalty, 4),
            "canonical_score": score,
            "reasons": reasons,
            "automatic_resolution": False,
            "requires_confirmation": True,
        }

    @classmethod
    def build(
        cls,
        *,
        canonical_conflicts: dict[str, Any],
        relationship_confidence: dict[str, Any],
        cross_franchise: dict[str, Any],
        graph_validation: dict[str, Any],
        entity_resolution_graph: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_candidates = cls._collect_candidates(
            canonical_conflicts,
            relationship_confidence,
        )

        scored = [
            cls._score_candidate(
                candidate,
                cross_franchise,
                graph_validation,
            )
            for candidate in raw_candidates
        ]

        grouped = defaultdict(list)
        for candidate in scored:
            grouped[
                (
                    candidate["subject_node_key"],
                    candidate["predicate"],
                )
            ].append(candidate)

        decisions = []
        for (subject, predicate), candidates in sorted(grouped.items()):
            candidates.sort(
                key=lambda item: (
                    -item["canonical_score"],
                    -item["source_count"],
                    cls._norm(item["value"]).casefold(),
                )
            )

            winner = candidates[0]
            runner_up = candidates[1] if len(candidates) > 1 else None
            margin = (
                round(
                    winner["canonical_score"]
                    - runner_up["canonical_score"],
                    4,
                )
                if runner_up else winner["canonical_score"]
            )

            if (
                winner["manual_confirmation"]
                and winner["canonical_score"] >= 0.8
            ):
                decision_type = "prefer_confirmed_value"
            elif (
                winner["source_count"] >= 2
                and winner["canonical_score"] >= 0.8
                and margin >= 0.1
            ):
                decision_type = "prefer_confirmed_consensus"
            elif (
                winner["canonical_score"] >= 0.75
                and margin >= 0.15
            ):
                decision_type = "prefer_highest_scored_value"
            else:
                decision_type = "manual_review_required"

            decisions.append({
                "decision_id": f"{subject}:{predicate}",
                "subject_node_key": subject,
                "predicate": predicate,
                "candidates": candidates,
                "recommended_value": (
                    winner["value"]
                    if decision_type
                    != "manual_review_required"
                    else None
                ),
                "decision_type": decision_type,
                "confidence": winner["canonical_score"],
                "score_margin": round(max(0.0, margin), 4),
                "explanation": {
                    "winning_reasons": winner["reasons"],
                    "winner_source_count": winner["source_count"],
                    "winner_sources": winner["sources"],
                    "boundary_penalty": winner[
                        "boundary_penalty"
                    ],
                    "conflict_penalty": winner[
                        "conflict_penalty"
                    ],
                },
                "automatic_resolution": False,
                "requires_confirmation": True,
            })

        decision_counts = defaultdict(int)
        for decision in decisions:
            decision_counts[decision["decision_type"]] += 1

        overall_confidence = (
            round(
                sum(item["confidence"] for item in decisions)
                / len(decisions),
                4,
            )
            if decisions else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "decisions": decisions,
            "summary": {
                "candidate_count": len(scored),
                "decision_count": len(decisions),
                "decision_type_counts": dict(
                    sorted(decision_counts.items())
                ),
                "manual_review_count": decision_counts.get(
                    "manual_review_required",
                    0,
                ),
                "overall_confidence": overall_confidence,
                "entity_resolution_candidate_count": len(
                    entity_resolution_graph.get(
                        "merge_proposals"
                    ) or []
                ),
            },
            "decision": {
                "status": (
                    "needs_review"
                    if decisions else "no_canonical_decisions"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
