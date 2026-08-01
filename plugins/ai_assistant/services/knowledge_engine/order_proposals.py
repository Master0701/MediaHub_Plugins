from __future__ import annotations

from collections import defaultdict
from typing import Any


class KnowledgeGraphOrderProposalService:
    """Erzeugt bestätigbare Reihenfolgevorschläge aus Graph-Entitäten."""

    def __init__(self, engine: Any):
        self.engine = engine

    @staticmethod
    def _year(entity: dict[str, Any]) -> int:
        value = entity.get("year")
        try:
            return int(value)
        except (TypeError, ValueError):
            return 9999

    @staticmethod
    def _title(entity: dict[str, Any]) -> str:
        return str(entity.get("title") or "").casefold()

    def _group_key(
        self,
        entity: dict[str, Any],
    ) -> tuple[str, str] | None:
        metadata = dict(entity.get("metadata") or {})
        franchise = str(
            metadata.get("franchise")
            or metadata.get("franchise_name")
            or ""
        ).strip()
        universe = str(
            metadata.get("universe")
            or metadata.get("universe_name")
            or ""
        ).strip()

        if franchise:
            return ("franchise", franchise)
        if universe:
            return ("universe", universe)
        return None

    def propose(self) -> dict[str, Any]:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for entity in self.engine.all_items():
            media_type = str(entity.get("media_type") or "")
            if media_type in {"franchise", "universe", "collection"}:
                continue
            key = self._group_key(entity)
            if key:
                groups[key].append(entity)

        proposals: list[dict[str, Any]] = []
        for (group_type, group_name), entities in groups.items():
            if len(entities) < 2:
                continue

            release_sorted = sorted(
                entities,
                key=lambda item: (
                    self._year(item),
                    self._title(item),
                ),
            )
            proposals.append(
                {
                    "kind": "order",
                    "order_type": "release",
                    "name": f"{group_name} – Veröffentlichungsreihenfolge",
                    "group_type": group_type,
                    "group_name": group_name,
                    "entity_ids": [
                        str(item.get("id")) for item in release_sorted
                    ],
                    "entity_titles": [
                        str(item.get("title")) for item in release_sorted
                    ],
                    "confidence": 0.88,
                    "reason": "Nach Veröffentlichungsjahr sortiert.",
                    "requires_confirmation": True,
                }
            )

            chronology_values = []
            for entity in entities:
                metadata = dict(entity.get("metadata") or {})
                chronology = metadata.get("chronology_index")
                if chronology is None:
                    chronology_values = []
                    break
                chronology_values.append(
                    (
                        float(chronology),
                        self._title(entity),
                        entity,
                    )
                )

            if chronology_values:
                chronology_values.sort(
                    key=lambda item: (item[0], item[1])
                )
                chronology_sorted = [
                    item[2] for item in chronology_values
                ]
                proposals.append(
                    {
                        "kind": "order",
                        "order_type": "chronological",
                        "name": f"{group_name} – Chronologische Reihenfolge",
                        "group_type": group_type,
                        "group_name": group_name,
                        "entity_ids": [
                            str(item.get("id"))
                            for item in chronology_sorted
                        ],
                        "entity_titles": [
                            str(item.get("title"))
                            for item in chronology_sorted
                        ],
                        "confidence": 0.95,
                        "reason": "Chronologie-Index aus bestätigten Metadaten.",
                        "requires_confirmation": True,
                    }
                )

        return {
            "schema_version": 1,
            "proposal_count": len(proposals),
            "proposals": proposals,
            "persisted_orders": False,
        }
