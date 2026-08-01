from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.knowledge_engine.models import OrderType, RelationType


class KnowledgeGraphBuilder:
    """Idempotenter Builder für bestätigte Medien, Beziehungen und Reihenfolgen."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.store = engine.store

    @staticmethod
    def _clean(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def _find_existing(
        self,
        *,
        title: str,
        media_type: str,
        year: int | None,
        external_ids: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        external_ids = {
            str(key): str(value)
            for key, value in (external_ids or {}).items()
            if value not in (None, "")
        }
        title_key = self._clean(title)
        type_key = self._clean(media_type)

        for entity in self.store.all_entities():
            stored_external = {
                str(key): str(value)
                for key, value in (entity.get("external_ids") or {}).items()
                if value not in (None, "")
            }
            if external_ids and any(
                stored_external.get(key) == value
                for key, value in external_ids.items()
            ):
                return entity

            titles = {
                self._clean(entity.get("title")),
                *{
                    self._clean(alias)
                    for alias in entity.get("aliases") or []
                },
            }
            if title_key not in titles:
                continue
            if self._clean(entity.get("media_type")) != type_key:
                continue
            stored_year = entity.get("year")
            if year is not None and stored_year not in (None, year):
                continue
            return entity
        return None

    def upsert_identity(
        self,
        identity: dict[str, Any],
        *,
        source: str = "confirmed_identity",
        confirmed_by_user: bool = False,
    ) -> dict[str, Any]:
        title = str(
            identity.get("title")
            or identity.get("canonical_title")
            or ""
        ).strip()
        if not title:
            raise ValueError("Für eine Graph-Entität wird ein Titel benötigt.")

        media_type = str(identity.get("media_type") or "other").strip()
        year = identity.get("year")
        if year is None:
            year = identity.get("release_year")

        aliases = sorted(
            {
                str(alias).strip()
                for alias in identity.get("aliases") or []
                if str(alias).strip()
            }
        )
        external_ids = dict(identity.get("external_ids") or {})
        metadata = {
            **dict(identity.get("metadata") or {}),
            "confirmed_by_user": bool(confirmed_by_user),
            "knowledge_identity_id": (
                identity.get("knowledge_identity_id")
                or identity.get("identity_id")
                or identity.get("id")
            ),
            "season": identity.get("season"),
            "episode": identity.get("episode"),
            "edition": identity.get("edition"),
        }
        source_record = {
            "source": source,
            "confidence": float(identity.get("confidence") or 1.0),
            "confirmed_by_user": bool(confirmed_by_user),
        }

        existing = self._find_existing(
            title=title,
            media_type=media_type,
            year=year,
            external_ids=external_ids,
        )
        if existing:
            record = self.store._data["entities"][str(existing["id"])]
            changed = False

            merged_aliases = sorted(
                {
                    *[str(item) for item in record.get("aliases") or []],
                    *aliases,
                }
            )
            if merged_aliases != list(record.get("aliases") or []):
                record["aliases"] = merged_aliases
                changed = True

            merged_external = {
                **dict(record.get("external_ids") or {}),
                **external_ids,
            }
            if merged_external != dict(record.get("external_ids") or {}):
                record["external_ids"] = merged_external
                changed = True

            merged_metadata = {
                **dict(record.get("metadata") or {}),
                **{
                    key: value
                    for key, value in metadata.items()
                    if value is not None
                },
            }
            if merged_metadata != dict(record.get("metadata") or {}):
                record["metadata"] = merged_metadata
                changed = True

            sources = list(record.get("sources") or [])
            if source_record not in sources:
                sources.append(source_record)
                record["sources"] = sources
                changed = True

            if changed:
                self.store.save()

            return {
                "status": "updated" if changed else "existing",
                "created": False,
                "entity": deepcopy(record),
            }

        entity = self.engine.create_entity(
            title,
            media_type,
            year=year,
            aliases=aliases,
            external_ids=external_ids,
            metadata=metadata,
            sources=[source_record],
        )
        return {
            "status": "created",
            "created": True,
            "entity": entity,
        }

    def connect_confirmed(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        label: str = "",
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        confirmed_by_user: bool = False,
    ) -> dict[str, Any]:
        relation_type = RelationType(str(relation_type)).value
        source_id = str(source_id)
        target_id = str(target_id)

        for relation in self.store.all_relations():
            if (
                str(relation.get("source_id")) == source_id
                and str(relation.get("target_id")) == target_id
                and str(relation.get("relation_type")) == relation_type
            ):
                return {
                    "status": "existing",
                    "created": False,
                    "relation": relation,
                }

        relation = self.engine.connect(
            source_id,
            target_id,
            relation_type,
            label=label,
            confidence=confidence,
            metadata={
                **dict(metadata or {}),
                "confirmed_by_user": bool(confirmed_by_user),
            },
            sources=list(sources or []),
        )
        return {
            "status": "created",
            "created": True,
            "relation": relation,
        }

    def create_or_get_order(
        self,
        name: str,
        order_type: str,
        entity_ids: list[str],
        *,
        description: str = "",
        notes: dict[str, str] | None = None,
        source: str = "confirmed_builder",
    ) -> dict[str, Any]:
        order_type = OrderType(str(order_type)).value
        normalized_ids = [str(item) for item in entity_ids]

        for order in self.store.all_orders():
            if (
                self._clean(order.get("name")) == self._clean(name)
                and str(order.get("order_type")) == order_type
            ):
                existing_ids = [
                    str(item.get("entity_id"))
                    for item in sorted(
                        order.get("entries") or [],
                        key=lambda item: int(item.get("position") or 0),
                    )
                ]
                if existing_ids == normalized_ids:
                    return {
                        "status": "existing",
                        "created": False,
                        "order": order,
                    }

        order = self.engine.create_order(
            name,
            order_type,
            normalized_ids,
            description=description,
            notes=notes,
            source=source,
        )
        return {
            "status": "created",
            "created": True,
            "order": order,
        }

    def propose_relationships(
        self,
        identities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        proposals: list[dict[str, Any]] = []
        mapped = [
            self.upsert_identity(
                identity,
                source="builder_proposal_context",
                confirmed_by_user=False,
            )["entity"]
            for identity in identities
        ]
        by_title = {
            self._clean(item.get("title")): item
            for item in mapped
        }

        for identity, entity in zip(identities, mapped):
            metadata = dict(identity.get("metadata") or {})
            franchise = str(
                identity.get("franchise")
                or metadata.get("franchise")
                or ""
            ).strip()
            universe = str(
                identity.get("universe")
                or metadata.get("universe")
                or ""
            ).strip()

            for group_name, relation_type, confidence in (
                (franchise, RelationType.FRANCHISE.value, 0.82),
                (universe, RelationType.UNIVERSE.value, 0.84),
            ):
                if group_name:
                    proposals.append(
                        {
                            "kind": "group_membership",
                            "entity_id": entity["id"],
                            "entity_title": entity["title"],
                            "relation_type": relation_type,
                            "group_name": group_name,
                            "confidence": confidence,
                            "reason": "Gruppenhinweis in bestätigten oder importierten Metadaten.",
                            "requires_confirmation": True,
                        }
                    )

            for hint in identity.get("relation_hints") or []:
                target = by_title.get(
                    self._clean(hint.get("target_title"))
                )
                if not target:
                    continue
                proposals.append(
                    {
                        "kind": "direct_relation",
                        "source_id": entity["id"],
                        "source_title": entity["title"],
                        "target_id": target["id"],
                        "target_title": target["title"],
                        "relation_type": str(
                            hint.get("relation_type")
                            or RelationType.PART_OF.value
                        ),
                        "confidence": float(
                            hint.get("confidence") or 0.75
                        ),
                        "reason": str(
                            hint.get("reason")
                            or "Beziehungshinweis aus Metadaten."
                        ),
                        "requires_confirmation": True,
                    }
                )

        return {
            "schema_version": 1,
            "strategy": "knowledge_graph_builder_v230",
            "entity_count": len(mapped),
            "proposal_count": len(proposals),
            "entities": mapped,
            "proposals": proposals,
            "persisted_relations": False,
        }
