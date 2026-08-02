from __future__ import annotations

from collections import defaultdict
from typing import Any


class NarrativeIntelligence:
    STRATEGY = "narrative_intelligence_v550"

    ARC_RELATIONS = {
        "introduces_conflict",
        "escalates_conflict",
        "resolves_conflict",
        "continues_story_arc",
        "concludes_story_arc",
        "begins_story_arc",
    }

    CHARACTER_RELATIONS = {
        "character_growth",
        "character_regression",
        "changes_allegiance",
        "becomes_leader",
        "redeems",
        "betrays",
    }

    MOTIF_RELATIONS = {
        "repeats_motif",
        "echoes_event",
        "mirrors_conflict",
        "foreshadows",
        "callbacks_to",
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
    def _collect_relationships(
        cls,
        fusion_result: dict[str, Any],
        semantic_reasoning: dict[str, Any],
        temporal_causal: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relationships: list[dict[str, Any]] = []

        def append_item(
            edge_type: Any,
            source_key: Any,
            target_key: Any,
            confidence: Any,
            origin: str,
        ) -> None:
            edge = cls._norm(edge_type).casefold()
            source = cls._norm(source_key)
            target = cls._norm(target_key)
            if not edge or not source or not target:
                return
            relationships.append({
                "edge_type": edge,
                "source_node_key": source,
                "target_node_key": target,
                "confidence": cls._confidence(confidence),
                "origin": origin,
            })

        for item in (fusion_result.get("fused_fields") or {}).values():
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if not isinstance(value, dict):
                continue
            append_item(
                value.get("edge_type"),
                value.get("source_node_key"),
                value.get("target_node_key"),
                item.get("confidence"),
                "multi_source_fusion",
            )

        for origin, payload in (
            ("semantic_reasoning", semantic_reasoning),
            ("temporal_causal_intelligence", temporal_causal),
        ):
            for item in payload.get("conclusions") or []:
                if not isinstance(item, dict):
                    continue
                append_item(
                    item.get("edge_type"),
                    item.get("source_node_key"),
                    item.get("target_node_key"),
                    item.get("confidence"),
                    origin,
                )

        unique = {}
        for item in relationships:
            key = (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            previous = unique.get(key)
            if previous is None or item["confidence"] > previous["confidence"]:
                unique[key] = item
        return list(unique.values())

    @classmethod
    def _derive_story_arcs(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relationships:
            if item["edge_type"] in cls.ARC_RELATIONS:
                outgoing[item["source_node_key"]].append(item)

        conclusions = []
        for source_key, items in outgoing.items():
            begins = [
                item for item in items
                if item["edge_type"] in {
                    "introduces_conflict",
                    "begins_story_arc",
                }
            ]
            resolves = [
                item for item in items
                if item["edge_type"] in {
                    "resolves_conflict",
                    "concludes_story_arc",
                }
            ]

            for start in begins:
                for end in resolves:
                    if start["target_node_key"] == end["target_node_key"]:
                        continue
                    conclusions.append({
                        "conclusion_type": "story_arc",
                        "edge_type": "story_arc_from_to",
                        "source_node_key": start["target_node_key"],
                        "target_node_key": end["target_node_key"],
                        "arc_owner_node_key": source_key,
                        "confidence": round(
                            min(
                                start["confidence"],
                                end["confidence"],
                            ) * 0.82,
                            4,
                        ),
                        "reason": (
                            f"{source_key} beginnt einen Konflikt bei "
                            f"{start['target_node_key']} und löst ihn bei "
                            f"{end['target_node_key']}."
                        ),
                        "evidence_path": [
                            dict(start),
                            dict(end),
                        ],
                        "requires_confirmation": True,
                    })
        return conclusions

    @classmethod
    def _derive_character_development(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_character: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relationships:
            if item["edge_type"] in cls.CHARACTER_RELATIONS:
                by_character[item["source_node_key"]].append(item)

        conclusions = []
        for character, items in by_character.items():
            if len(items) < 2:
                continue
            ordered = sorted(
                items,
                key=lambda item: (
                    item["target_node_key"],
                    item["edge_type"],
                ),
            )
            conclusions.append({
                "conclusion_type": "character_development",
                "edge_type": "has_character_arc",
                "source_node_key": character,
                "target_node_key": (
                    "character_arc:"
                    + character.replace(":", "-")
                ),
                "confidence": round(
                    min(item["confidence"] for item in ordered) * 0.8,
                    4,
                ),
                "reason": (
                    f"Für {character} wurden mehrere aufeinander bezogene "
                    "Entwicklungsschritte erkannt."
                ),
                "development_steps": [
                    {
                        "edge_type": item["edge_type"],
                        "target_node_key": item["target_node_key"],
                        "origin": item["origin"],
                    }
                    for item in ordered
                ],
                "evidence_path": [dict(item) for item in ordered],
                "requires_confirmation": True,
            })
        return conclusions

    @classmethod
    def _derive_repeated_motifs(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        motifs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relationships:
            if item["edge_type"] in cls.MOTIF_RELATIONS:
                motifs[item["target_node_key"]].append(item)

        conclusions = []
        for motif, items in motifs.items():
            sources = sorted({
                item["source_node_key"]
                for item in items
            })
            if len(sources) < 2:
                continue
            conclusions.append({
                "conclusion_type": "repeated_motif",
                "edge_type": "shared_narrative_motif",
                "source_node_key": sources[0],
                "target_node_key": motif,
                "related_source_node_keys": sources[1:],
                "confidence": round(
                    min(item["confidence"] for item in items) * 0.78,
                    4,
                ),
                "reason": (
                    f"Das Motiv {motif} wurde in mehreren "
                    "Handlungsabschnitten erkannt."
                ),
                "evidence_path": [dict(item) for item in items],
                "requires_confirmation": True,
            })
        return conclusions

    @classmethod
    def _find_conflicts(
        cls,
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        known = {
            (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            )
            for item in relationships
        }
        opposing = {
            "character_growth": "character_regression",
            "character_regression": "character_growth",
            "redeems": "betrays",
            "betrays": "redeems",
            "begins_story_arc": "concludes_story_arc",
            "concludes_story_arc": "begins_story_arc",
        }

        conflicts = []
        seen = set()
        for item in relationships:
            opposite = opposing.get(item["edge_type"])
            if not opposite:
                continue
            key = (
                opposite,
                item["source_node_key"],
                item["target_node_key"],
            )
            if key not in known:
                continue
            unique_key = (
                item["source_node_key"],
                item["target_node_key"],
                *sorted((item["edge_type"], opposite)),
            )
            if unique_key in seen:
                continue
            seen.add(unique_key)
            conflicts.append({
                "conflict_type": "narrative_contradiction",
                "source_node_key": item["source_node_key"],
                "target_node_key": item["target_node_key"],
                "relationship_a": item["edge_type"],
                "relationship_b": opposite,
                "reason": (
                    "Für dieselbe Figur oder denselben Handlungsbogen wurden "
                    "widersprüchliche narrative Entwicklungen erkannt."
                ),
                "requires_confirmation": True,
            })
        return conflicts

    @classmethod
    def analyze(
        cls,
        *,
        fusion_result: dict[str, Any],
        semantic_reasoning: dict[str, Any],
        temporal_causal_intelligence: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relationships = cls._collect_relationships(
            fusion_result,
            semantic_reasoning,
            temporal_causal_intelligence,
        )

        conclusions = (
            cls._derive_story_arcs(relationships)
            + cls._derive_character_development(relationships)
            + cls._derive_repeated_motifs(relationships)
        )

        unique = []
        seen = set()
        for item in conclusions:
            key = (
                item.get("conclusion_type"),
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        conflicts = cls._find_conflicts(relationships)
        confidence = (
            round(
                sum(item["confidence"] for item in unique) / len(unique),
                4,
            )
            if unique
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
            "conclusions": unique,
            "conflicts": conflicts,
            "summary": {
                "input_relationship_count": len(relationships),
                "story_arc_count": sum(
                    item.get("conclusion_type") == "story_arc"
                    for item in unique
                ),
                "character_arc_count": sum(
                    item.get("conclusion_type")
                    == "character_development"
                    for item in unique
                ),
                "motif_count": sum(
                    item.get("conclusion_type") == "repeated_motif"
                    for item in unique
                ),
                "conclusion_count": len(unique),
                "conflict_count": len(conflicts),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if conflicts or unique
                    else "no_new_conclusions"
                ),
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
