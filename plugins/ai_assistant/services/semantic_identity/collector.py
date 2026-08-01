from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.semantic_identity.weights import group_weight, source_weight


class IdentityEvidenceCollector:
    """Bereitet Kandidatenbelege für spätere Entscheidungen nachvollziehbar auf."""

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _evidence_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("source") or "other").strip().lower(),
            str(item.get("independent_group") or "other").strip().lower(),
            str(item.get("value") or "").strip().casefold(),
        )

    def _prepare_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        prepared: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        duplicate_count = 0

        for raw in evidence:
            item = deepcopy(raw)
            key = self._evidence_key(item)
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)

            source = str(item.get("source") or "other").strip().lower()
            group = str(
                item.get("independent_group") or "other"
            ).strip().lower()
            confidence = self._clamp(item.get("confidence"))
            source_factor = source_weight(source)
            group_factor = group_weight(group)
            weighted = confidence * source_factor * group_factor

            item.update(
                {
                    "source": source,
                    "independent_group": group,
                    "confidence": round(confidence, 4),
                    "source_weight": round(source_factor, 4),
                    "group_weight": round(group_factor, 4),
                    "weighted_strength": round(weighted, 4),
                    "used_for_group_score": False,
                }
            )
            prepared.append(item)

        prepared.sort(
            key=lambda item: (
                item["weighted_strength"],
                item["confidence"],
            ),
            reverse=True,
        )
        return prepared, duplicate_count

    @staticmethod
    def _group_summary(
        evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in evidence:
            groups.setdefault(item["independent_group"], []).append(item)

        result: list[dict[str, Any]] = []
        for name, items in groups.items():
            strongest = max(
                items,
                key=lambda item: (
                    item["weighted_strength"],
                    item["confidence"],
                ),
            )
            strongest["used_for_group_score"] = True
            result.append(
                {
                    "group": name,
                    "evidence_count": len(items),
                    "strongest_source": strongest["source"],
                    "strongest_confidence": strongest["confidence"],
                    "weighted_strength": strongest["weighted_strength"],
                    "supporting_sources": sorted(
                        {item["source"] for item in items}
                    ),
                }
            )

        result.sort(
            key=lambda item: item["weighted_strength"],
            reverse=True,
        )
        return result

    @staticmethod
    def _combined_strength(groups: list[dict[str, Any]]) -> float:
        if not groups:
            return 0.0

        # Probabilistische Kombination unabhängiger Beleggruppen.
        product = 1.0
        for item in groups:
            strength = max(
                0.0,
                min(0.97, float(item.get("weighted_strength") or 0.0)),
            )
            product *= 1.0 - strength

        score = 1.0 - product

        # Ein einzelner Beleg bleibt absichtlich vorsichtig.
        if len(groups) == 1:
            score *= 0.72
        elif len(groups) == 2:
            score *= 0.90

        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _coverage(groups: list[dict[str, Any]]) -> dict[str, Any]:
        names = {str(item.get("group") or "") for item in groups}
        considered = {
            "filename",
            "online",
            "visual_text",
            "visual",
            "knowledge",
            "fingerprint",
            "subtitle",
            "audio",
        }
        return {
            "present_groups": sorted(name for name in names if name),
            "missing_groups": sorted(considered - names),
            "independent_group_count": len(names),
        }

    def collect(
        self,
        candidate_result: dict[str, Any] | None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(candidate_result or {})
        output: list[dict[str, Any]] = []

        for candidate in source.get("candidates") or []:
            item = deepcopy(candidate)
            prepared, duplicates = self._prepare_evidence(
                list(item.get("evidence") or [])
            )
            groups = self._group_summary(prepared)
            combined = self._combined_strength(groups)
            coverage = self._coverage(groups)

            item["evidence"] = prepared
            item["evidence_summary"] = {
                "raw_evidence_count": len(candidate.get("evidence") or []),
                "unique_evidence_count": len(prepared),
                "duplicate_evidence_count": duplicates,
                "independent_group_count": coverage[
                    "independent_group_count"
                ],
                "groups": groups,
                "coverage": coverage,
                "combined_evidence_strength": combined,
                "combined_evidence_strength_percent": round(
                    combined * 100,
                    1,
                ),
            }
            item["evidence_strength"] = combined
            item["evidence_strength_percent"] = round(combined * 100, 1)
            item["stage"] = "evidence_collected"
            output.append(item)

        output.sort(
            key=lambda item: (
                item.get("evidence_strength") or 0.0,
                item.get("candidate_score") or 0.0,
                item.get("source_count") or 0,
            ),
            reverse=True,
        )

        return {
            "schema_version": 2,
            "stage": "evidence_collector",
            "decision_made": False,
            "candidate_count": len(output),
            "candidates": output,
            "best_candidate": output[0] if output else None,
            "source_stage": source.get("stage"),
            "sources_considered": list(
                source.get("sources_considered") or []
            ),
            "collection_policy": {
                "duplicate_evidence_removed": True,
                "strongest_evidence_per_group_scores_fully": True,
                "repeated_same_group_does_not_multiply_confidence": True,
                "single_group_penalty": True,
            },
            "limitations": [
                "v2.2.1 sammelt und gewichtet Belege, trifft aber noch keine endgültige Entscheidung.",
                "Widersprüche zwischen Kandidaten werden erst in v2.2.2 bewertet.",
                "Die endgültige Vertrauensberechnung folgt in v2.2.3.",
            ],
        }
