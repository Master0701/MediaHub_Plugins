from __future__ import annotations

from collections import defaultdict
from typing import Any


class CharacterMemoryEngine:
    STRATEGY = "character_memory_engine_v650"

    MEMORY_TYPES = {
        "relationship",
        "timeline_event",
        "evolution",
        "conflict",
        "identity",
        "trauma",
        "achievement",
        "loss",
        "alliance",
        "betrayal",
        "promise",
        "secret",
        "status",
    }

    IMPORTANCE_WEIGHTS = {
        "death": 1.0,
        "resurrection": 1.0,
        "betrayal": 0.95,
        "identity_change": 0.92,
        "marriage": 0.9,
        "parenthood": 0.9,
        "coronation": 0.88,
        "power_gain": 0.82,
        "power_loss": 0.82,
        "alliance": 0.78,
        "imprisonment": 0.76,
        "release": 0.72,
        "relationship": 0.7,
        "status_change": 0.68,
        "timeline_event": 0.65,
        "evolution": 0.65,
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
    def _importance(
        cls,
        memory_type: str,
        event_type: str | None,
        confidence: float,
    ) -> float:
        key = cls._norm(event_type).casefold()
        base = cls.IMPORTANCE_WEIGHTS.get(
            key,
            cls.IMPORTANCE_WEIGHTS.get(memory_type, 0.55),
        )
        return round(max(0.0, min(1.0, base * 0.7 + confidence * 0.3)), 4)

    @classmethod
    def _collect_relationship_memories(
        cls,
        graph: dict[str, Any],
    ) -> list[dict[str, Any]]:
        memories = []

        for edge in graph.get("edges") or []:
            if not isinstance(edge, dict):
                continue

            character = cls._norm(edge.get("source_node_key"))
            target = cls._norm(edge.get("target_node_key"))
            relation = cls._norm(edge.get("edge_type")).casefold()
            if not character or not target or not relation:
                continue

            confidence = cls._float(edge.get("confidence"), 0.6)
            memories.append({
                "character_node_key": character,
                "memory_type": "relationship",
                "event_type": relation,
                "target_node_key": target,
                "sequence_index": 0,
                "summary": f"{relation}: {target}",
                "confidence": confidence,
                "importance": cls._importance(
                    "relationship",
                    relation,
                    confidence,
                ),
                "origin": graph.get("strategy") or "unknown",
                "requires_confirmation": True,
            })

        return memories

    @classmethod
    def _collect_timeline_memories(
        cls,
        timeline: dict[str, Any],
    ) -> list[dict[str, Any]]:
        memories = []

        for character_timeline in timeline.get("timelines") or []:
            if not isinstance(character_timeline, dict):
                continue

            character = cls._norm(
                character_timeline.get("character_node_key")
            )
            for event in character_timeline.get("events") or []:
                if not isinstance(event, dict):
                    continue

                event_type = cls._norm(
                    event.get("event_type")
                ).casefold()
                confidence = cls._float(
                    event.get("confidence"), 0.6
                )
                memories.append({
                    "character_node_key": character
                    or cls._norm(
                        event.get("character_node_key")
                    ),
                    "memory_type": "timeline_event",
                    "event_type": event_type,
                    "target_node_key": cls._norm(
                        event.get("target_node_key")
                    ) or None,
                    "sequence_index": int(
                        event.get("sequence_index") or 0
                    ),
                    "summary": cls._norm(
                        event.get("sentence")
                    ) or event_type,
                    "confidence": confidence,
                    "importance": cls._importance(
                        "timeline_event",
                        event_type,
                        confidence,
                    ),
                    "origin": timeline.get("strategy") or "unknown",
                    "requires_confirmation": True,
                })

        return memories

    @classmethod
    def _collect_evolution_memories(
        cls,
        evolution: dict[str, Any],
    ) -> list[dict[str, Any]]:
        memories = []

        for character_evolution in evolution.get("evolutions") or []:
            if not isinstance(character_evolution, dict):
                continue

            character = cls._norm(
                character_evolution.get("character_node_key")
            )
            for change in character_evolution.get("changes") or []:
                if not isinstance(change, dict):
                    continue

                evolution_type = cls._norm(
                    change.get("evolution_type")
                ).casefold()
                confidence = cls._float(
                    change.get("confidence"), 0.6
                )
                summary = cls._norm(change.get("sentence"))
                if not summary:
                    before = cls._norm(change.get("from_value"))
                    after = cls._norm(change.get("to_value"))
                    summary = (
                        f"{before} -> {after}"
                        if before or after
                        else evolution_type
                    )

                memories.append({
                    "character_node_key": character
                    or cls._norm(
                        change.get("character_node_key")
                    ),
                    "memory_type": "evolution",
                    "event_type": evolution_type,
                    "target_node_key": cls._norm(
                        change.get("target_node_key")
                    ) or None,
                    "sequence_index": int(
                        change.get("sequence_index") or 0
                    ),
                    "summary": summary,
                    "confidence": confidence,
                    "importance": cls._importance(
                        "evolution",
                        evolution_type,
                        confidence,
                    ),
                    "origin": evolution.get("strategy") or "unknown",
                    "requires_confirmation": True,
                })

        return memories

    @classmethod
    def _deduplicate(
        cls,
        memories: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unique = {}
        for memory in memories:
            key = (
                memory["character_node_key"],
                memory["memory_type"],
                memory["event_type"],
                memory.get("target_node_key"),
                memory["summary"],
            )
            existing = unique.get(key)
            if existing is None or memory["confidence"] > existing["confidence"]:
                unique[key] = memory
        return list(unique.values())

    @classmethod
    def build(
        cls,
        *,
        character_relationship_graph: dict[str, Any],
        character_timeline: dict[str, Any],
        character_evolution: dict[str, Any],
        relationship_confidence: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        memories = cls._deduplicate(
            cls._collect_relationship_memories(
                character_relationship_graph
            )
            + cls._collect_timeline_memories(
                character_timeline
            )
            + cls._collect_evolution_memories(
                character_evolution
            )
        )

        confidence_lookup = {}
        for assessment in (
            relationship_confidence.get("assessments") or []
        ):
            if not isinstance(assessment, dict):
                continue
            key = (
                cls._norm(assessment.get("relation_type")).casefold(),
                cls._norm(assessment.get("source_node_key")),
                cls._norm(assessment.get("target_node_key")),
            )
            confidence_lookup[key] = cls._float(
                assessment.get("confidence"), 0.5
            )

        for memory in memories:
            if memory["memory_type"] != "relationship":
                continue

            key = (
                memory["event_type"],
                memory["character_node_key"],
                memory.get("target_node_key") or "",
            )
            if key in confidence_lookup:
                confidence = confidence_lookup[key]
                memory["confidence"] = confidence
                memory["importance"] = cls._importance(
                    memory["memory_type"],
                    memory["event_type"],
                    confidence,
                )

        by_character = defaultdict(list)
        for memory in memories:
            if memory["character_node_key"]:
                by_character[memory["character_node_key"]].append(memory)

        profiles = []
        for character, character_memories in sorted(by_character.items()):
            character_memories.sort(
                key=lambda item: (
                    item["sequence_index"],
                    -item["importance"],
                    item["memory_type"],
                    item["event_type"],
                )
            )

            important = [
                item for item in character_memories
                if item["importance"] >= 0.75
            ]

            profiles.append({
                "character_node_key": character,
                "memories": character_memories,
                "memory_count": len(character_memories),
                "important_memory_count": len(important),
                "important_memories": important,
                "requires_confirmation": True,
            })

        type_counts = defaultdict(int)
        for memory in memories:
            type_counts[memory["memory_type"]] += 1

        overall_confidence = (
            round(
                sum(memory["confidence"] for memory in memories)
                / len(memories),
                4,
            )
            if memories else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "profiles": profiles,
            "summary": {
                "character_count": len(profiles),
                "memory_count": len(memories),
                "important_memory_count": sum(
                    profile["important_memory_count"]
                    for profile in profiles
                ),
                "memory_type_counts": dict(sorted(type_counts.items())),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if memories else "no_character_memories"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
