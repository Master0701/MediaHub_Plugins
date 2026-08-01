from __future__ import annotations

from collections import defaultdict
from typing import Any


class KnowledgeGraphCompletenessService:
    """Bewertet Vollständigkeit aus Metadaten, Beziehungen und Reihenfolgen."""

    GROUP_RELATIONS = {
        "franchise",
        "universe",
        "collection",
        "part_of",
    }

    def __init__(self, engine: Any):
        self.engine = engine

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _entity_summary(entity: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": entity.get("id"),
            "title": entity.get("title"),
            "year": entity.get("year"),
            "media_type": entity.get("media_type"),
        }

    def _metadata_groups(
        self,
        entities: list[dict[str, Any]],
    ) -> dict[tuple[str, str], list[dict[str, Any]]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for entity in entities:
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
                grouped[("franchise", franchise)].append(entity)
            if universe:
                grouped[("universe", universe)].append(entity)

        return grouped

    def _relation_groups(
        self,
        entities_by_id: dict[str, dict[str, Any]],
    ) -> dict[tuple[str, str], list[dict[str, Any]]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for relation in self.engine.store.all_relations():
            relation_type = str(relation.get("relation_type") or "")
            if relation_type not in self.GROUP_RELATIONS:
                continue

            source = entities_by_id.get(str(relation.get("source_id")))
            target = entities_by_id.get(str(relation.get("target_id")))
            if not source or not target:
                continue

            target_type = str(target.get("media_type") or "")
            if target_type not in {"franchise", "universe", "collection"}:
                continue

            group_type = (
                target_type
                if target_type in {"franchise", "universe"}
                else "collection"
            )
            grouped[(group_type, str(target.get("title") or ""))].append(source)

        return grouped

    def _order_groups(
        self,
        entities_by_id: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        groups = []

        for order in self.engine.store.all_orders():
            entries = sorted(
                order.get("entries") or [],
                key=lambda item: int(item.get("position") or 0),
            )
            members = [
                entities_by_id.get(str(entry.get("entity_id")))
                for entry in entries
            ]
            members = [item for item in members if item]
            if not members:
                continue

            groups.append(
                {
                    "group_type": "order",
                    "group_name": str(order.get("name") or "Reihenfolge"),
                    "order_type": order.get("order_type"),
                    "members": members,
                    "expected_entries": [
                        {
                            "title": item.get("title"),
                            "year": item.get("year"),
                            "media_type": item.get("media_type"),
                        }
                        for item in members
                    ],
                    "limitations": [],
                    "source": "knowledge_graph_order",
                }
            )

        return groups

    @staticmethod
    def _expected_entries(
        members: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        expected_map: dict[str, dict[str, Any]] = {}

        for member in members:
            metadata = dict(member.get("metadata") or {})
            for item in metadata.get("expected_entries") or []:
                if isinstance(item, str):
                    entry = {
                        "title": item,
                        "year": None,
                        "media_type": None,
                    }
                elif isinstance(item, dict) and item.get("title"):
                    entry = {
                        "title": str(item.get("title")),
                        "year": item.get("year"),
                        "media_type": item.get("media_type"),
                    }
                else:
                    continue

                key = " ".join(
                    str(entry.get("title") or "")
                    .strip()
                    .casefold()
                    .split()
                )
                if key:
                    expected_map[key] = entry

        return list(expected_map.values())

    def analyze(self) -> dict[str, Any]:
        entities = list(self.engine.all_items())
        entities_by_id = {
            str(item.get("id")): item
            for item in entities
        }

        groups: list[dict[str, Any]] = []

        merged_groups: dict[
            tuple[str, str],
            list[dict[str, Any]],
        ] = defaultdict(list)

        for source in (
            self._metadata_groups(entities),
            self._relation_groups(entities_by_id),
        ):
            for key, members in source.items():
                known_ids = {
                    str(item.get("id"))
                    for item in merged_groups[key]
                }
                for member in members:
                    if str(member.get("id")) not in known_ids:
                        merged_groups[key].append(member)
                        known_ids.add(str(member.get("id")))

        for (group_type, group_name), members in merged_groups.items():
            expected = self._expected_entries(members)
            limitations = []
            if not expected:
                expected = [
                    {
                        "title": member.get("title"),
                        "year": member.get("year"),
                        "media_type": member.get("media_type"),
                    }
                    for member in members
                ]
                limitations.append(
                    "Keine separate Soll-Liste vorhanden; "
                    "die aktuell bestätigten Gruppenmitglieder gelten "
                    "vorläufig als vollständiger Bestand."
                )

            groups.append(
                {
                    "group_type": group_type,
                    "group_name": group_name,
                    "members": members,
                    "expected_entries": expected,
                    "limitations": limitations,
                    "source": "knowledge_graph_group",
                }
            )

        groups.extend(self._order_groups(entities_by_id))

        analyzed_groups = []
        total_missing = 0

        for group in groups:
            members = group.get("members") or []
            expected = group.get("expected_entries") or []

            present_titles = {
                self._normalize(member.get("title")): member
                for member in members
            }
            missing = [
                item
                for item in expected
                if self._normalize(item.get("title")) not in present_titles
            ]
            total_missing += len(missing)

            analyzed_groups.append(
                {
                    "group_type": group.get("group_type"),
                    "group_name": group.get("group_name"),
                    "order_type": group.get("order_type"),
                    "source": group.get("source"),
                    "member_count": len(members),
                    "expected_count": len(expected),
                    "missing_count": len(missing),
                    "complete": not missing,
                    "members": [
                        self._entity_summary(item)
                        for item in members
                    ],
                    "missing": missing,
                    "limitations": list(
                        group.get("limitations") or []
                    ),
                }
            )

        return {
            "schema_version": 2,
            "strategy": "knowledge_graph_completeness_v246",
            "group_count": len(analyzed_groups),
            "missing_count": total_missing,
            "groups": analyzed_groups,
            "automatic_changes": False,
        }
