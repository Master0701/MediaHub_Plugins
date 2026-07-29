from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.knowledge_engine.models import (
    KnowledgeEntity,
    KnowledgeOrder,
    KnowledgeRelation,
    OrderType,
    RelationType,
)


class KnowledgeStore:
    def __init__(self, base_dir: Path):
        supplied_path = Path(base_dir)
        database_suffixes = {".db", ".sqlite", ".sqlite3"}

        if (
            supplied_path.is_file()
            or supplied_path.suffix.casefold() in database_suffixes
        ):
            runtime_root = supplied_path.parent
            self.legacy_database = supplied_path
        else:
            runtime_root = supplied_path
            self.legacy_database = None

        self.base_dir = runtime_root
        self.data_dir = runtime_root / "knowledge_graph"
        self.data_file = self.data_dir / "knowledge_graph.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "entities": {},
            "relations": {},
            "orders": {},
        }

    def _load(self) -> dict[str, Any]:
        if not self.data_file.is_file():
            return self._empty()
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(data, dict):
            return self._empty()
        data.setdefault("schema_version", 1)
        data.setdefault("entities", {})
        data.setdefault("relations", {})
        data.setdefault("orders", {})
        return data

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary_file = self.data_file.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary_file.replace(self.data_file)

    def add_entity(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        self._data["entities"][entity.id] = entity.as_dict()
        self.save()
        return entity

    def add_relation(
        self,
        relation: KnowledgeRelation,
    ) -> KnowledgeRelation:
        self._data["relations"][relation.id] = relation.as_dict()
        self.save()
        return relation

    def add_order(self, order: KnowledgeOrder) -> KnowledgeOrder:
        self._data["orders"][order.id] = order.as_dict()
        self.save()
        return order

    def all_entities(self) -> list[dict[str, Any]]:
        return sorted(
            (
                dict(item)
                for item in self._data["entities"].values()
                if isinstance(item, dict)
            ),
            key=lambda item: (
                str(item.get("title") or "").casefold(),
                int(item.get("year") or 0),
            ),
        )

    def all_relations(self) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in self._data["relations"].values()
            if isinstance(item, dict)
        ]

    def all_orders(self) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in self._data["orders"].values()
            if isinstance(item, dict)
        ]

    def find_entities(self, query: str) -> list[dict[str, Any]]:
        needle = str(query).strip().casefold()
        if not needle:
            return self.all_entities()

        matches = []
        for entity in self.all_entities():
            values = [
                str(entity.get("title") or ""),
                str(entity.get("year") or ""),
                str(entity.get("media_type") or ""),
                *[str(item) for item in entity.get("aliases") or []],
                *[
                    str(item)
                    for item in (entity.get("external_ids") or {}).values()
                ],
            ]
            if any(needle in value.casefold() for value in values):
                matches.append(entity)
        return matches

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        item = self._data["entities"].get(str(entity_id))
        return dict(item) if isinstance(item, dict) else None

    def relations_for(self, entity_id: str) -> list[dict[str, Any]]:
        return [
            dict(relation)
            for relation in self._data["relations"].values()
            if isinstance(relation, dict)
            and (
                relation.get("source_id") == entity_id
                or relation.get("target_id") == entity_id
            )
        ]


    def outgoing_relations(self, entity_id: str, relation_type: str | None = None) -> list[dict[str, Any]]:
        result = []
        for relation in self.all_relations():
            if relation.get("source_id") != str(entity_id):
                continue
            if relation_type and relation.get("relation_type") != str(relation_type):
                continue
            result.append(relation)
        return result

    def incoming_relations(self, entity_id: str, relation_type: str | None = None) -> list[dict[str, Any]]:
        result = []
        for relation in self.all_relations():
            if relation.get("target_id") != str(entity_id):
                continue
            if relation_type and relation.get("relation_type") != str(relation_type):
                continue
            result.append(relation)
        return result

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        item = self._data["orders"].get(str(order_id))
        return dict(item) if isinstance(item, dict) else None

    def orders_for_entity(self, entity_id: str) -> list[dict[str, Any]]:
        result = []
        for order in self._data["orders"].values():
            if not isinstance(order, dict):
                continue
            entries = order.get("entries") or []
            if any(entry.get("entity_id") == entity_id for entry in entries):
                result.append(dict(order))
        return result

    def status(self) -> dict[str, Any]:
        orders = self.all_orders()
        counts = {
            order_type.value: sum(
                1
                for order in orders
                if order.get("order_type") == order_type.value
            )
            for order_type in OrderType
        }
        return {
            "schema_version": self._data.get("schema_version", 1),
            "data_file": str(self.data_file),
            "legacy_database": (
                str(self.legacy_database)
                if self.legacy_database is not None
                else None
            ),
            "legacy_database_exists": bool(
                self.legacy_database is not None
                and self.legacy_database.is_file()
            ),
            "entities": len(self._data["entities"]),
            "relations": len(self._data["relations"]),
            "orders": len(self._data["orders"]),
            "order_types": counts,
            "supported_relations": [item.value for item in RelationType],
            "supported_orders": [item.value for item in OrderType],
        }
