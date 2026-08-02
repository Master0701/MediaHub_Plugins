from __future__ import annotations

import re
from typing import Any


class StoryTimelineBuilder:
    STRATEGY = "story_timeline_builder_v580"

    TEMPORAL_MARKERS = (
        ("flashback", (r"\bzuvor\b", r"\bfrüher\b", r"\brückblende\b")),
        (
            "flashforward",
            (r"\bspäter\b", r"\bin der zukunft\b", r"\bjahre später\b"),
        ),
        (
            "parallel",
            (r"\bgleichzeitig\b", r"\bwährenddessen\b", r"\bunterdessen\b"),
        ),
        (
            "after",
            (
                r"\bdanach\b",
                r"\bdaraufhin\b",
                r"\banschließend\b",
                r"\bkurz darauf\b",
            ),
        ),
        (
            "before",
            (r"\bbevor\b", r"\bzuvor\b", r"\bvorher\b"),
        ),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _position(node_key: Any) -> int | None:
        match = re.match(
            r"^(?:conflict|resolution|development):(\d+):",
            str(node_key or ""),
        )
        return int(match.group(1)) if match else None

    @classmethod
    def _detect_marker(cls, sentence: str) -> str | None:
        lowered = cls._norm(sentence).casefold()
        for marker, patterns in cls.TEMPORAL_MARKERS:
            if any(re.search(pattern, lowered) for pattern in patterns):
                return marker
        return None

    @classmethod
    def _chapter_for_index(cls, index: int, total: int) -> str:
        if total <= 1:
            return "single"
        ratio = index / max(total - 1, 1)
        if ratio < 0.2:
            return "opening"
        if ratio < 0.75:
            return "middle"
        if ratio < 0.92:
            return "finale"
        return "epilogue"

    @classmethod
    def build(
        cls,
        *,
        narrative_extraction: dict[str, Any],
        story_arc_linking: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        for item in narrative_extraction.get("relations") or []:
            if not isinstance(item, dict):
                continue
            node_key = cls._norm(item.get("target_node_key"))
            if not node_key:
                continue
            sentence = cls._norm(item.get("sentence"))
            events.append({
                "node_key": node_key,
                "owner_node_key": cls._norm(
                    item.get("source_node_key")
                ),
                "edge_type": cls._norm(item.get("edge_type")).casefold(),
                "position": cls._position(node_key),
                "sentence": sentence,
                "temporal_marker": cls._detect_marker(sentence),
                "confidence": float(item.get("confidence") or 0.5),
            })

        events.sort(
            key=lambda item: (
                item["position"] is None,
                item["position"] or 0,
                item["node_key"],
            )
        )

        total = len(events)
        for index, event in enumerate(events):
            event["sequence_index"] = index
            event["chapter"] = cls._chapter_for_index(index, total)

        links: list[dict[str, Any]] = []
        for index, event in enumerate(events[:-1]):
            next_event = events[index + 1]
            relation = "before"
            if next_event.get("temporal_marker") == "parallel":
                relation = "parallel_to"
            elif next_event.get("temporal_marker") == "flashback":
                relation = "flashback_to"
            elif next_event.get("temporal_marker") == "flashforward":
                relation = "flashforward_to"

            links.append({
                "relation_type": relation,
                "source_node_key": event["node_key"],
                "target_node_key": next_event["node_key"],
                "confidence": round(
                    min(
                        event["confidence"],
                        next_event["confidence"],
                    ) * 0.86,
                    4,
                ),
                "requires_confirmation": True,
            })

        arc_windows: list[dict[str, Any]] = []
        for arc in story_arc_linking.get("arcs") or []:
            if not isinstance(arc, dict):
                continue
            arc_windows.append({
                "arc_type": arc.get("arc_type"),
                "owner_node_key": arc.get("owner_node_key"),
                "start_node_key": arc.get("start_node_key"),
                "end_node_key": arc.get("end_node_key"),
                "confidence": float(arc.get("confidence") or 0.5),
                "requires_confirmation": True,
            })

        chapter_counts = {}
        for event in events:
            chapter = event["chapter"]
            chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1

        confidence = (
            round(
                sum(link["confidence"] for link in links) / len(links),
                4,
            )
            if links
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
            "events": events,
            "links": links,
            "arc_windows": arc_windows,
            "chapters": chapter_counts,
            "summary": {
                "event_count": len(events),
                "link_count": len(links),
                "parallel_link_count": sum(
                    item["relation_type"] == "parallel_to"
                    for item in links
                ),
                "flashback_link_count": sum(
                    item["relation_type"] == "flashback_to"
                    for item in links
                ),
                "flashforward_link_count": sum(
                    item["relation_type"] == "flashforward_to"
                    for item in links
                ),
                "arc_window_count": len(arc_windows),
                "chapter_count": len(chapter_counts),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": "needs_review" if events else "no_timeline",
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
