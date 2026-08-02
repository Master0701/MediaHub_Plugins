from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


class CharacterTimelineEngine:
    STRATEGY = "character_timeline_engine_v630"

    EVENT_TYPES = {
        "birth",
        "death",
        "marriage",
        "parenthood",
        "coronation",
        "rule_start",
        "rule_end",
        "imprisonment",
        "release",
        "betrayal",
        "alliance",
        "identity_reveal",
        "transformation",
        "disappearance",
        "return",
        "battle",
        "rescue",
        "capture",
        "promotion",
        "exile",
    }

    TEMPORAL_MARKERS = (
        ("before", (r"\bzuvor\b", r"\bvorher\b", r"\bbevor\b")),
        ("after", (r"\bdanach\b", r"\bdaraufhin\b", r"\bspäter\b")),
        ("parallel", (r"\bgleichzeitig\b", r"\bwährenddessen\b", r"\bunterdessen\b")),
        ("flashback", (r"\brückblende\b", r"\bfrüher\b")),
        ("flashforward", (r"\bvorausblende\b", r"\bin der zukunft\b")),
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
    def _marker(cls, text: Any) -> str | None:
        lowered = cls._norm(text).casefold()
        for marker, patterns in cls.TEMPORAL_MARKERS:
            if any(re.search(pattern, lowered) for pattern in patterns):
                return marker
        return None

    @classmethod
    def _infer_event_type(cls, item: dict[str, Any]) -> str | None:
        candidates = (
            item.get("event_type"),
            item.get("edge_type"),
            item.get("relation_type"),
            item.get("arc_type"),
        )
        for value in candidates:
            event_type = cls._norm(value).casefold()
            if event_type in cls.EVENT_TYPES:
                return event_type

        sentence = cls._norm(item.get("sentence")).casefold()
        patterns = (
            ("marriage", (r"\bheirat", r"\behe")),
            ("birth", (r"\bgeboren\b", r"\bgeburt\b")),
            ("death", (r"\bstirbt\b", r"\bgestorben\b", r"\btod\b")),
            ("imprisonment", (r"\bgefängnis\b", r"\beingesperrt\b")),
            ("release", (r"\bbefreit\b", r"\bfreigelassen\b")),
            ("coronation", (r"\bgekrönt\b", r"\bkönig\b")),
            ("rescue", (r"\brettet\b", r"\bgerettet\b")),
            ("capture", (r"\bentführt\b", r"\bgefangen\b")),
            ("battle", (r"\bkämpft\b", r"\bschlacht\b")),
            ("betrayal", (r"\bverrät\b", r"\bverrat\b")),
            ("alliance", (r"\bverbündet\b", r"\ballianz\b")),
            ("return", (r"\bkehrt zurück\b", r"\brückkehr\b")),
            ("disappearance", (r"\bverschwindet\b", r"\bvermisst\b")),
        )
        for event_type, regexes in patterns:
            if any(re.search(pattern, sentence) for pattern in regexes):
                return event_type
        return None

    @classmethod
    def _collect_events(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        events = []

        for payload in payloads:
            strategy = cls._norm(payload.get("strategy"))
            items = (
                payload.get("events")
                or payload.get("relations")
                or payload.get("edges")
                or payload.get("conclusions")
                or payload.get("assessments")
                or []
            )

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue

                event_type = cls._infer_event_type(item)
                if not event_type:
                    continue

                character = cls._norm(
                    item.get("character_node_key")
                    or item.get("source_node_key")
                    or item.get("owner_node_key")
                )
                target = cls._norm(
                    item.get("target_node_key")
                    or item.get("related_node_key")
                )
                if not character:
                    continue

                sentence = cls._norm(item.get("sentence"))
                position = item.get("sequence_index")
                if position is None:
                    position = item.get("position")
                try:
                    position_value = int(position)
                except (TypeError, ValueError):
                    position_value = index

                events.append({
                    "event_id": cls._norm(item.get("id")) or (
                        f"{event_type}:{character}:{position_value}"
                    ),
                    "event_type": event_type,
                    "character_node_key": character,
                    "target_node_key": target or None,
                    "sequence_index": position_value,
                    "temporal_marker": cls._marker(sentence),
                    "sentence": sentence,
                    "confidence": cls._float(
                        item.get("confidence"), 0.6
                    ),
                    "origin": strategy or "unknown",
                    "requires_confirmation": True,
                })

        return events

    @classmethod
    def build(
        cls,
        *,
        character_relationship_graph: dict[str, Any],
        story_timeline: dict[str, Any],
        relationship_confidence: dict[str, Any],
        narrative_intelligence: dict[str, Any],
        event_intelligence: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        events = cls._collect_events(
            character_relationship_graph,
            story_timeline,
            relationship_confidence,
            narrative_intelligence,
            event_intelligence,
        )

        by_character = defaultdict(list)
        for event in events:
            by_character[event["character_node_key"]].append(event)

        timelines = []
        for character, character_events in sorted(by_character.items()):
            character_events.sort(
                key=lambda item: (
                    item["sequence_index"],
                    item["event_type"],
                    item["event_id"],
                )
            )

            links = []
            for left, right in zip(character_events, character_events[1:]):
                relation_type = "before"
                if right.get("temporal_marker") == "parallel":
                    relation_type = "parallel_to"
                elif right.get("temporal_marker") == "flashback":
                    relation_type = "flashback_to"
                elif right.get("temporal_marker") == "flashforward":
                    relation_type = "flashforward_to"

                links.append({
                    "relation_type": relation_type,
                    "source_event_id": left["event_id"],
                    "target_event_id": right["event_id"],
                    "confidence": round(
                        min(
                            left["confidence"],
                            right["confidence"],
                        ) * 0.9,
                        4,
                    ),
                    "requires_confirmation": True,
                })

            timelines.append({
                "character_node_key": character,
                "events": character_events,
                "links": links,
                "event_count": len(character_events),
                "link_count": len(links),
                "requires_confirmation": True,
            })

        event_type_counts = defaultdict(int)
        for event in events:
            event_type_counts[event["event_type"]] += 1

        overall_confidence = (
            round(
                sum(event["confidence"] for event in events)
                / len(events),
                4,
            )
            if events else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "timelines": timelines,
            "summary": {
                "character_count": len(timelines),
                "event_count": len(events),
                "event_type_counts": dict(
                    sorted(event_type_counts.items())
                ),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if events else "no_character_events"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
