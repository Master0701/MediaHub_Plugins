from __future__ import annotations

from pathlib import Path
from typing import Any

from services.knowledge_engine.models import (
    KnowledgeEntity,
    KnowledgeOrder,
    KnowledgeRelation,
    OrderEntry,
    OrderType,
    RelationType,
)
from services.knowledge_engine.store import KnowledgeStore


class KnowledgeEngine:
    """Kompatible Fassade für alten Wissensindex und neuen Wissensgraph."""

    API_VERSION = 2

    def __init__(self, base_dir: Path):
        self.store = KnowledgeStore(base_dir)

    def ensure_schema(self) -> None:
        """Legt die persistente Graph-Struktur sicher und zerstörungsfrei an."""

        self.store.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.store.data_file.is_file():
            self.store.save()

    def initialize(self) -> None:
        """Kompatibilitätsalias für bestehende Startabläufe."""

        self.ensure_schema()

    def create_entity(
        self,
        title: str,
        media_type: str,
        *,
        year: int | None = None,
        aliases: list[str] | None = None,
        external_ids: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entity = KnowledgeEntity(
            title=str(title).strip(),
            media_type=str(media_type).strip() or "other",
            year=year,
            aliases=list(aliases or []),
            external_ids=dict(external_ids or {}),
            metadata=dict(metadata or {}),
        )
        return self.store.add_entity(entity).as_dict()

    def connect(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        label: str = "",
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relation = KnowledgeRelation(
            source_id=str(source_id),
            target_id=str(target_id),
            relation_type=RelationType(str(relation_type)),
            label=str(label),
            confidence=max(0.0, min(1.0, float(confidence))),
            metadata=dict(metadata or {}),
        )
        return self.store.add_relation(relation).as_dict()

    def create_order(
        self,
        name: str,
        order_type: str,
        entity_ids: list[str],
        *,
        description: str = "",
        notes: dict[str, str] | None = None,
        source: str = "local",
    ) -> dict[str, Any]:
        note_map = dict(notes or {})
        order = KnowledgeOrder(
            name=str(name),
            order_type=OrderType(str(order_type)),
            description=str(description),
            source=str(source),
            entries=[
                OrderEntry(
                    entity_id=str(entity_id),
                    position=index,
                    note=str(note_map.get(str(entity_id)) or ""),
                )
                for index, entity_id in enumerate(entity_ids, start=1)
            ],
        )
        return self.store.add_order(order).as_dict()

    def _enrich(self, entity: dict[str, Any]) -> dict[str, Any]:
        entity_id = str(entity.get("id") or "")
        return {
            **dict(entity),
            "relations": self.store.relations_for(entity_id),
            "orders": self.store.orders_for_entity(entity_id),
        }

    def all_items(self) -> list[dict[str, Any]]:
        """Liefert alle Wissensobjekte für bestehende GUI- und Web-Aufrufe."""

        return [
            self._enrich(entity)
            for entity in self.store.all_entities()
        ]

    def search(self, query: str) -> dict[str, Any]:
        entities = self.store.find_entities(query)
        matches = [self._enrich(entity) for entity in entities]
        return {
            "query": str(query),
            "matches": matches,
            "results": matches,
            "match_count": len(matches),
        }

    def stats(self) -> dict[str, Any]:
        """Kompatibler Statistikaufruf für die bestehende Plugin-Oberfläche."""

        status = self.store.status()
        return {
            "api_version": self.API_VERSION,
            "schema_version": status["schema_version"],
            "entities": status["entities"],
            "relations": status["relations"],
            "orders": status["orders"],
            "order_types": dict(status["order_types"]),
            "data_file": status["data_file"],
            "legacy_database": status["legacy_database"],
            "legacy_database_exists": status["legacy_database_exists"],
        }

    def status(self) -> dict[str, Any]:
        status = self.store.status()
        return {
            **status,
            "api_version": self.API_VERSION,
            "initialized": self.store.data_file.is_file(),
            "compatibility_methods": [
                "ensure_schema",
                "initialize",
                "stats",
                "status",
                "all_items",
                "search",
                "seed_demo_data",
                "create_entity",
                "connect",
                "create_order",
            ],
        }

    def seed_demo_data(self) -> dict[str, Any]:
        """Legt idempotente Beispieldaten für Suche und Reihenfolgen an."""

        self.ensure_schema()
        titles = {
            str(item.get("title") or "").casefold(): item
            for item in self.store.all_entities()
        }
        created_entities: list[dict[str, Any]] = []

        demo_entities = (
            {
                "title": "Stargate",
                "media_type": "movie",
                "year": 1994,
                "aliases": ["Stargate – Der Film"],
            },
            {
                "title": "Stargate SG-1",
                "media_type": "series",
                "year": 1997,
                "aliases": ["Stargate Kommando SG-1"],
            },
            {
                "title": "Stargate Atlantis",
                "media_type": "series",
                "year": 2004,
                "aliases": ["SGA"],
            },
        )

        for values in demo_entities:
            key = values["title"].casefold()
            if key in titles:
                continue
            created = self.create_entity(**values)
            titles[key] = created
            created_entities.append(created)

        movie = titles["stargate"]
        sg1 = titles["stargate sg-1"]
        atlantis = titles["stargate atlantis"]

        created_relations: list[dict[str, Any]] = []
        relation_keys = {
            (
                str(item.get("source_id")),
                str(item.get("target_id")),
                str(item.get("relation_type")),
            )
            for item in self.store.all_relations()
        }
        relation_specs = (
            (movie["id"], sg1["id"], RelationType.CONTINUES_IN.value),
            (sg1["id"], atlantis["id"], RelationType.SPIN_OFF.value),
            (movie["id"], atlantis["id"], RelationType.UNIVERSE.value),
        )
        for source_id, target_id, relation_type in relation_specs:
            key = (str(source_id), str(target_id), relation_type)
            if key in relation_keys:
                continue
            created_relations.append(
                self.connect(source_id, target_id, relation_type)
            )
            relation_keys.add(key)

        existing_orders = {
            (
                str(item.get("name") or "").casefold(),
                str(item.get("order_type") or ""),
            )
            for item in self.store.all_orders()
        }
        created_orders: list[dict[str, Any]] = []
        order_specs = (
            (
                "Stargate – Veröffentlichung",
                OrderType.RELEASE.value,
                [movie["id"], sg1["id"], atlantis["id"]],
            ),
            (
                "Stargate – empfohlene Anschau-Reihenfolge",
                OrderType.WATCH.value,
                [movie["id"], sg1["id"], atlantis["id"]],
            ),
            (
                "Stargate – chronologisch",
                OrderType.CHRONOLOGICAL.value,
                [movie["id"], sg1["id"], atlantis["id"]],
            ),
        )
        for name, order_type, entity_ids in order_specs:
            key = (name.casefold(), order_type)
            if key in existing_orders:
                continue
            created_orders.append(
                self.create_order(name, order_type, entity_ids)
            )
            existing_orders.add(key)

        return {
            "created_entities": len(created_entities),
            "created_relations": len(created_relations),
            "created_orders": len(created_orders),
            "entities": created_entities,
            "relations": created_relations,
            "orders": created_orders,
            "stats": self.stats(),
        }
