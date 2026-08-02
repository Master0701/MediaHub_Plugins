from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


class CharacterEvolutionEngine:
    STRATEGY = "character_evolution_engine_v640"

    EVOLUTION_TYPES = {
        "role_change",
        "rank_change",
        "power_gain",
        "power_loss",
        "identity_change",
        "alignment_change",
        "moral_change",
        "injury",
        "recovery",
        "death",
        "resurrection",
        "ability_gain",
        "ability_loss",
        "status_change",
        "loyalty_change",
    }

    PATTERNS = (
        ("rank_change", (r"\bwird könig\b", r"\bwird königin\b", r"\bgekrönt\b", r"\bbefördert\b")),
        ("power_gain", (r"\berhält .*macht\b", r"\bgewinnt .*kraft\b", r"\bstärker\b")),
        ("power_loss", (r"\bverliert .*macht\b", r"\bgeschwächt\b", r"\bentmachtet\b")),
        ("identity_change", (r"\balias\b", r"\bgeheime identität\b", r"\bnimmt .*identität\b")),
        ("alignment_change", (r"\bwechselt die seite\b", r"\bverbündet sich\b", r"\bwendet sich gegen\b")),
        ("moral_change", (r"\bbereut\b", r"\bgeläutert\b", r"\bverfällt\b", r"\bkorrupt\b")),
        ("injury", (r"\bverletzt\b", r"\bverwundet\b", r"\bverstümmelt\b")),
        ("recovery", (r"\bgenest\b", r"\berholt sich\b", r"\bwird geheilt\b")),
        ("death", (r"\bstirbt\b", r"\bgetötet\b", r"\btod\b")),
        ("resurrection", (r"\bwiederbelebt\b", r"\bkehrt von den toten zurück\b")),
        ("ability_gain", (r"\blernt .*fähigkeit\b", r"\berlangt .*fähigkeit\b")),
        ("ability_loss", (r"\bverliert .*fähigkeit\b", r"\bkann nicht mehr\b")),
        ("loyalty_change", (r"\bverrät\b", r"\bwechselt die loyalität\b")),
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
    def _infer_type(cls, item: dict[str, Any]) -> str | None:
        for key in ("evolution_type", "event_type", "relation_type", "edge_type"):
            value = cls._norm(item.get(key)).casefold()
            if value in cls.EVOLUTION_TYPES:
                return value

        sentence = cls._norm(item.get("sentence")).casefold()
        for evolution_type, patterns in cls.PATTERNS:
            if any(re.search(pattern, sentence) for pattern in patterns):
                return evolution_type
        return None

    @classmethod
    def _collect_changes(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        changes = []

        for payload in payloads:
            strategy = cls._norm(payload.get("strategy")) or "unknown"
            items = (
                payload.get("events")
                or payload.get("changes")
                or payload.get("relations")
                or payload.get("edges")
                or payload.get("conclusions")
                or payload.get("assessments")
                or []
            )

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue

                evolution_type = cls._infer_type(item)
                if not evolution_type:
                    continue

                character = cls._norm(
                    item.get("character_node_key")
                    or item.get("source_node_key")
                    or item.get("owner_node_key")
                )
                if not character:
                    continue

                sequence = item.get("sequence_index")
                if sequence is None:
                    sequence = item.get("position")
                try:
                    sequence_index = int(sequence)
                except (TypeError, ValueError):
                    sequence_index = index

                changes.append({
                    "change_id": cls._norm(item.get("id")) or (
                        f"{evolution_type}:{character}:{sequence_index}"
                    ),
                    "character_node_key": character,
                    "evolution_type": evolution_type,
                    "from_value": item.get("from_value"),
                    "to_value": item.get("to_value"),
                    "target_node_key": cls._norm(
                        item.get("target_node_key")
                    ) or None,
                    "sequence_index": sequence_index,
                    "sentence": cls._norm(item.get("sentence")),
                    "confidence": cls._float(
                        item.get("confidence"), 0.6
                    ),
                    "origin": strategy,
                    "requires_confirmation": True,
                })

        return changes

    @classmethod
    def _detect_conflicts(
        cls,
        changes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        conflicts = []
        by_character_type = defaultdict(list)

        for change in changes:
            by_character_type[
                (
                    change["character_node_key"],
                    change["evolution_type"],
                )
            ].append(change)

        for (character, evolution_type), group in by_character_type.items():
            targets = {
                cls._norm(change.get("to_value"))
                for change in group
                if cls._norm(change.get("to_value"))
            }
            if len(targets) > 1:
                conflicts.append({
                    "conflict_type": "evolution_target_conflict",
                    "character_node_key": character,
                    "evolution_type": evolution_type,
                    "target_values": sorted(targets),
                    "requires_confirmation": True,
                })

        return conflicts

    @classmethod
    def build(
        cls,
        *,
        character_timeline: dict[str, Any],
        character_relationship_graph: dict[str, Any],
        relationship_confidence: dict[str, Any],
        narrative_intelligence: dict[str, Any],
        character_identity_fusion: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timeline_events = []
        for timeline in character_timeline.get("timelines") or []:
            if not isinstance(timeline, dict):
                continue
            timeline_events.extend(timeline.get("events") or [])

        changes = cls._collect_changes(
            {"strategy": "character_timeline_engine_v630", "events": timeline_events},
            character_relationship_graph,
            relationship_confidence,
            narrative_intelligence,
            character_identity_fusion,
        )

        by_character = defaultdict(list)
        for change in changes:
            by_character[change["character_node_key"]].append(change)

        evolutions = []
        for character, character_changes in sorted(by_character.items()):
            character_changes.sort(
                key=lambda item: (
                    item["sequence_index"],
                    item["evolution_type"],
                    item["change_id"],
                )
            )

            before_after_links = []
            for left, right in zip(character_changes, character_changes[1:]):
                before_after_links.append({
                    "relation_type": "evolves_to",
                    "source_change_id": left["change_id"],
                    "target_change_id": right["change_id"],
                    "confidence": round(
                        min(
                            left["confidence"],
                            right["confidence"],
                        ) * 0.9,
                        4,
                    ),
                    "requires_confirmation": True,
                })

            evolutions.append({
                "character_node_key": character,
                "changes": character_changes,
                "links": before_after_links,
                "change_count": len(character_changes),
                "link_count": len(before_after_links),
                "requires_confirmation": True,
            })

        conflicts = cls._detect_conflicts(changes)

        type_counts = defaultdict(int)
        for change in changes:
            type_counts[change["evolution_type"]] += 1

        overall_confidence = (
            round(
                sum(change["confidence"] for change in changes)
                / len(changes),
                4,
            )
            if changes else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "evolutions": evolutions,
            "conflicts": conflicts,
            "summary": {
                "character_count": len(evolutions),
                "change_count": len(changes),
                "conflict_count": len(conflicts),
                "evolution_type_counts": dict(sorted(type_counts.items())),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if changes or conflicts
                    else "no_character_evolution"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
