from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


class StoryArcLinker:
    STRATEGY = "story_arc_linker_v570"

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _position(node_key: str) -> int | None:
        match = re.match(
            r"^(?:conflict|resolution|development):(\d+):",
            str(node_key or ""),
        )
        return int(match.group(1)) if match else None

    @classmethod
    def link(
        cls,
        *,
        narrative_extraction: dict[str, Any],
        narrative_intelligence: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relations = [
            dict(item)
            for item in narrative_extraction.get("relations") or []
            if isinstance(item, dict)
        ]

        by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in relations:
            owner = cls._norm(item.get("source_node_key"))
            if owner:
                by_owner[owner].append(item)

        arcs: list[dict[str, Any]] = []

        for owner, items in by_owner.items():
            conflicts = sorted(
                (
                    item for item in items
                    if item.get("edge_type") == "introduces_conflict"
                ),
                key=lambda item: cls._position(
                    str(item.get("target_node_key") or "")
                ) or 0,
            )
            resolutions = sorted(
                (
                    item for item in items
                    if item.get("edge_type") == "resolves_conflict"
                ),
                key=lambda item: cls._position(
                    str(item.get("target_node_key") or "")
                ) or 0,
            )

            used: set[int] = set()
            for conflict in conflicts:
                conflict_pos = cls._position(
                    str(conflict.get("target_node_key") or "")
                )
                candidates = []
                for index, resolution in enumerate(resolutions):
                    if index in used:
                        continue
                    resolution_pos = cls._position(
                        str(resolution.get("target_node_key") or "")
                    )
                    if (
                        conflict_pos is None
                        or resolution_pos is None
                        or resolution_pos >= conflict_pos
                    ):
                        candidates.append((index, resolution))

                if not candidates:
                    continue

                index, resolution = candidates[0]
                used.add(index)
                confidence = min(
                    float(conflict.get("confidence") or 0.5),
                    float(resolution.get("confidence") or 0.5),
                ) * 0.84
                arcs.append({
                    "arc_type": "conflict_resolution_arc",
                    "owner_node_key": owner,
                    "start_node_key": conflict.get("target_node_key"),
                    "end_node_key": resolution.get("target_node_key"),
                    "confidence": round(confidence, 4),
                    "evidence_path": [conflict, resolution],
                    "requires_confirmation": True,
                })

            growth = sorted(
                (
                    item for item in items
                    if item.get("edge_type") == "character_growth"
                ),
                key=lambda item: cls._position(
                    str(item.get("target_node_key") or "")
                ) or 0,
            )
            if len(growth) >= 2:
                arcs.append({
                    "arc_type": "character_development_arc",
                    "owner_node_key": owner,
                    "start_node_key": growth[0].get("target_node_key"),
                    "end_node_key": growth[-1].get("target_node_key"),
                    "step_node_keys": [
                        item.get("target_node_key") for item in growth
                    ],
                    "confidence": round(
                        min(
                            float(item.get("confidence") or 0.5)
                            for item in growth
                        ) * 0.8,
                        4,
                    ),
                    "evidence_path": growth,
                    "requires_confirmation": True,
                })

        story_arcs = [
            item
            for item in narrative_intelligence.get("conclusions") or []
            if isinstance(item, dict)
            and item.get("conclusion_type") == "story_arc"
        ]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in story_arcs:
            owner = cls._norm(item.get("arc_owner_node_key"))
            if owner:
                grouped[owner].append(item)

        for owner, items in grouped.items():
            if len(items) < 2:
                continue
            arcs.append({
                "arc_type": "linked_story_arc_chain",
                "owner_node_key": owner,
                "start_node_key": items[0].get("source_node_key"),
                "end_node_key": items[-1].get("target_node_key"),
                "arc_count": len(items),
                "linked_arcs": items,
                "confidence": round(
                    min(float(item.get("confidence") or 0.5) for item in items)
                    * 0.82,
                    4,
                ),
                "requires_confirmation": True,
            })

        confidence = (
            round(sum(item["confidence"] for item in arcs) / len(arcs), 4)
            if arcs else 0.0
        )
        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "arcs": arcs,
            "summary": {
                "input_relation_count": len(relations),
                "arc_count": len(arcs),
                "conflict_resolution_arc_count": sum(
                    item["arc_type"] == "conflict_resolution_arc"
                    for item in arcs
                ),
                "character_development_arc_count": sum(
                    item["arc_type"] == "character_development_arc"
                    for item in arcs
                ),
                "linked_story_arc_chain_count": sum(
                    item["arc_type"] == "linked_story_arc_chain"
                    for item in arcs
                ),
                "overall_confidence": confidence,
            },
            "decision": {
                "status": "needs_review" if arcs else "no_linked_arcs",
                "confidence": confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
