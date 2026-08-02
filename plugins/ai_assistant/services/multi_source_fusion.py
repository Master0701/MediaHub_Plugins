from __future__ import annotations

from collections import defaultdict
import json
from typing import Any


class MultiSourceFusion:
    STRATEGY = "multi_source_fusion_v520"

    DEFAULT_SOURCE_WEIGHTS = {
        "user_confirmation": 1.00,
        "local_knowledge": 0.95,
        "knowledge_graph": 0.92,
        "reasoning_intelligence": 0.90,
        "semantic_engine": 0.84,
        "tmdb": 0.82,
        "tvdb": 0.82,
        "wikipedia": 0.74,
        "ocr": 0.52,
        "audio": 0.58,
        "frame": 0.55,
        "unknown": 0.50,
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
    def _source_name(cls, item: dict[str, Any], fallback: str) -> str:
        return cls._norm(
            item.get("source_name")
            or item.get("source")
            or item.get("provider")
            or item.get("group")
            or fallback
            or "unknown"
        ).casefold()

    @classmethod
    def _source_weight(
        cls,
        source_name: str,
        overrides: dict[str, float] | None,
    ) -> float:
        if overrides and source_name in overrides:
            return cls._confidence(overrides[source_name], 0.5)
        return cls.DEFAULT_SOURCE_WEIGHTS.get(
            source_name,
            cls.DEFAULT_SOURCE_WEIGHTS["unknown"],
        )

    @classmethod
    def _value_key(cls, value: Any) -> str:
        if isinstance(value, dict):
            edge_type = cls._norm(
                value.get("edge_type") or value.get("relation_type")
            )
            source_key = cls._norm(value.get("source_node_key"))
            target_key = cls._norm(value.get("target_node_key"))

            if edge_type and source_key and target_key:
                return "|".join(
                    (
                        "relationship",
                        edge_type.casefold(),
                        source_key.casefold(),
                        target_key.casefold(),
                    )
                )

            title = cls._norm(value.get("title") or value.get("name"))
            year = cls._norm(value.get("year"))
            media_type = cls._norm(
                value.get("media_type") or value.get("type")
            )
            identity_key = "|".join(
                part.casefold()
                for part in (title, year, media_type)
                if part
            )
            if identity_key:
                return identity_key

            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).casefold()

        if isinstance(value, (list, tuple, set)):
            return "|".join(
                sorted(cls._norm(item).casefold() for item in value)
            )

        return cls._norm(value).casefold()

    @classmethod
    def _extract_candidates(
        cls,
        source_name: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        for item in payload.get("candidates") or []:
            if not isinstance(item, dict):
                continue
            field = cls._norm(item.get("field") or item.get("kind"))
            value = item.get("value")
            if field and value not in (None, "", [], {}):
                candidates.append({
                    "field": field,
                    "value": value,
                    "confidence": cls._confidence(item.get("confidence")),
                    "source_name": cls._source_name(item, source_name),
                    "reason": cls._norm(item.get("reason")),
                    "evidence": item.get("evidence") or [],
                })

        identity = payload.get("identity")
        if isinstance(identity, dict):
            for field in (
                "title",
                "year",
                "media_type",
                "season",
                "episode",
                "edition",
            ):
                value = identity.get(field)
                if value not in (None, "", [], {}):
                    candidates.append({
                        "field": field,
                        "value": value,
                        "confidence": cls._confidence(
                            identity.get("confidence")
                            or payload.get("confidence")
                        ),
                        "source_name": cls._source_name(identity, source_name),
                        "reason": cls._norm(identity.get("reason")),
                        "evidence": identity.get("evidence") or [],
                    })

        for field in (
            "title",
            "year",
            "media_type",
            "season",
            "episode",
            "edition",
        ):
            value = payload.get(field)
            if value not in (None, "", [], {}):
                candidates.append({
                    "field": field,
                    "value": value,
                    "confidence": cls._confidence(payload.get("confidence")),
                    "source_name": cls._source_name(payload, source_name),
                    "reason": cls._norm(payload.get("reason")),
                    "evidence": payload.get("evidence") or [],
                })

        for conclusion in payload.get("conclusions") or []:
            if not isinstance(conclusion, dict):
                continue

            base_field = cls._norm(
                conclusion.get("field")
                or conclusion.get("conclusion_type")
                or "relationship"
            )
            edge_type = cls._norm(conclusion.get("edge_type"))
            source_key = cls._norm(conclusion.get("source_node_key"))
            target_key = cls._norm(conclusion.get("target_node_key"))

            value = {
                "edge_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
            }
            if not all(value.values()):
                continue

            field = ":".join(
                (
                    base_field.casefold(),
                    edge_type.casefold(),
                    source_key.casefold(),
                    target_key.casefold(),
                )
            )

            candidates.append({
                "field": field,
                "value": value,
                "confidence": cls._confidence(
                    conclusion.get("confidence")
                ),
                "source_name": cls._source_name(
                    conclusion,
                    source_name,
                ),
                "reason": cls._norm(conclusion.get("reason")),
                "evidence": conclusion.get("evidence_path") or [],
            })

        return candidates

    @classmethod
    def fuse(
        cls,
        *,
        sources: dict[str, dict[str, Any]],
        source_weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for source_name, payload in (sources or {}).items():
            if not isinstance(payload, dict):
                continue
            for candidate in cls._extract_candidates(source_name, payload):
                candidate["source_weight"] = cls._source_weight(
                    candidate["source_name"],
                    source_weights,
                )
                candidate["weighted_confidence"] = round(
                    candidate["confidence"] * candidate["source_weight"],
                    4,
                )
                candidate["value_key"] = cls._value_key(candidate["value"])
                grouped[candidate["field"]].append(candidate)

        fused_fields: dict[str, dict[str, Any]] = {}
        conflicts: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        evidence_log: list[dict[str, Any]] = []

        for field, candidates in grouped.items():
            by_value: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for candidate in candidates:
                by_value[candidate["value_key"]].append(candidate)
                evidence_log.append({
                    "field": field,
                    "value": candidate["value"],
                    "source_name": candidate["source_name"],
                    "confidence": candidate["confidence"],
                    "source_weight": candidate["source_weight"],
                    "weighted_confidence": candidate["weighted_confidence"],
                    "reason": candidate["reason"],
                    "evidence": candidate["evidence"],
                })

            ranked: list[dict[str, Any]] = []
            for value_key, supporters in by_value.items():
                remaining = 1.0
                for supporter in supporters:
                    remaining *= 1.0 - supporter["weighted_confidence"]
                combined = round(1.0 - remaining, 4)
                ranked.append({
                    "value_key": value_key,
                    "value": supporters[0]["value"],
                    "confidence": combined,
                    "support_count": len(supporters),
                    "sources": sorted({
                        item["source_name"] for item in supporters
                    }),
                    "evidence_path": supporters,
                })

                if len(supporters) > 1:
                    duplicates.append({
                        "field": field,
                        "value": supporters[0]["value"],
                        "support_count": len(supporters),
                        "sources": sorted({
                            item["source_name"] for item in supporters
                        }),
                    })

            ranked.sort(
                key=lambda item: (
                    item["confidence"],
                    item["support_count"],
                ),
                reverse=True,
            )
            winner = ranked[0]
            alternatives = ranked[1:]

            fused_fields[field] = {
                "value": winner["value"],
                "confidence": winner["confidence"],
                "support_count": winner["support_count"],
                "sources": winner["sources"],
                "evidence_path": winner["evidence_path"],
                "alternatives": alternatives,
                "requires_confirmation": True,
            }

            if alternatives:
                conflicts.append({
                    "field": field,
                    "selected": winner,
                    "alternatives": alternatives,
                    "reason": (
                        "Multiple distinct values were reported for the same "
                        "field."
                    ),
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                })

        overall_confidence = (
            round(
                sum(
                    item["confidence"]
                    for item in fused_fields.values()
                ) / len(fused_fields),
                4,
            )
            if fused_fields
            else 0.0
        )

        return {
            "strategy": cls.STRATEGY,
            "fused_fields": fused_fields,
            "conflicts": conflicts,
            "duplicates": duplicates,
            "evidence_log": evidence_log,
            "summary": {
                "source_count": len(sources or {}),
                "field_count": len(fused_fields),
                "conflict_count": len(conflicts),
                "duplicate_count": len(duplicates),
                "evidence_count": len(evidence_log),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": "needs_review" if conflicts else "fused",
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
