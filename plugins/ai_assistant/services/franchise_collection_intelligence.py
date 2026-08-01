from __future__ import annotations

import re
from typing import Any


class FranchiseCollectionIntelligence:
    """Baut bestätigungspflichtige Franchise- und Reihenfolge-Vorschläge."""

    RELATION_TYPES = {
        "sequel_of",
        "prequel_of",
        "spin_off_of",
        "crossover_with",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _key(
        cls,
        node_type: str,
        title: str,
        year: int | None = None,
    ) -> str:
        base = f"{node_type}:{cls._norm(title).casefold()}"
        return f"{base}:{year}" if year is not None else base

    @classmethod
    def _clean_franchise_title(cls, title: str) -> str:
        value = cls._norm(title)
        value = re.sub(r"\s+\(\d{4}\)$", "", value)
        value = re.sub(
            r"\s*[:\-–—]\s*"
            r"(?:lost kingdom|the lost kingdom|part\s+\d+|teil\s+\d+)$",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return value.strip(" :-–—")

    @classmethod
    def _media_node(
        cls,
        *,
        title: str,
        year: int | None,
        node_type: str,
        source_id: Any,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "key": cls._key(node_type, title, year),
            "node_type": node_type,
            "title": cls._norm(title),
            "year": year,
            "confidence": 0.94,
            "metadata": {
                "franchise_intelligence": (
                    "franchise_collection_intelligence_v422"
                ),
            },
            "reason": reason,
            "source_id": source_id,
            "requires_confirmation": True,
        }

    @classmethod
    def _normalize_installments(
        cls,
        *,
        main_node: dict[str, Any],
        classified_fields: dict[str, Any],
        relationship_proposal: dict[str, Any],
    ) -> list[dict[str, Any]]:
        primary = dict(
            dict(classified_fields or {}).get("primary_values")
            or {}
        )

        installments: list[dict[str, Any]] = []

        main_title = cls._norm(main_node.get("title"))
        main_year = main_node.get("year") or primary.get("release_year")
        main_type = cls._norm(main_node.get("node_type") or "media")

        if main_title:
            installments.append({
                "title": main_title,
                "year": main_year,
                "node_type": main_type,
                "role": "current",
                "chronology_index": primary.get("chronology_index"),
                "release_index": primary.get("release_index"),
            })

        predecessor = dict(primary.get("predecessor") or {})
        if cls._norm(predecessor.get("title")):
            installments.append({
                "title": cls._norm(predecessor.get("title")),
                "year": predecessor.get("year"),
                "node_type": main_type,
                "role": "predecessor",
                "chronology_index": predecessor.get("chronology_index"),
                "release_index": predecessor.get("release_index"),
            })

        for item in primary.get("franchise_installments") or []:
            if not isinstance(item, dict):
                continue
            title = cls._norm(item.get("title"))
            if not title:
                continue
            installments.append({
                "title": title,
                "year": item.get("year"),
                "node_type": cls._norm(
                    item.get("node_type") or main_type
                ),
                "role": cls._norm(item.get("role") or "related"),
                "chronology_index": item.get("chronology_index"),
                "release_index": item.get("release_index"),
            })

        # Relationship edges can introduce additional media nodes.
        for edge in dict(relationship_proposal or {}).get("edges") or []:
            edge_type = edge.get("edge_type")
            if edge_type not in cls.RELATION_TYPES:
                continue

            metadata = dict(edge.get("metadata") or {})
            related = metadata.get("related_media")
            if not isinstance(related, dict):
                continue

            title = cls._norm(related.get("title"))
            if not title:
                continue

            installments.append({
                "title": title,
                "year": related.get("year"),
                "node_type": cls._norm(
                    related.get("node_type") or main_type
                ),
                "role": edge_type,
                "chronology_index": related.get("chronology_index"),
                "release_index": related.get("release_index"),
            })

        dedup: dict[tuple[str, int | None, str], dict[str, Any]] = {}
        for item in installments:
            key = (
                cls._norm(item.get("title")).casefold(),
                item.get("year"),
                cls._norm(item.get("node_type")).casefold(),
            )
            existing = dedup.get(key)
            if existing is None:
                dedup[key] = item
                continue

            # Preserve the more informative ordering hints.
            for field in ("chronology_index", "release_index"):
                if existing.get(field) is None and item.get(field) is not None:
                    existing[field] = item.get(field)

        return list(dedup.values())

    @classmethod
    def _sort_installments(
        cls,
        installments: list[dict[str, Any]],
        *,
        mode: str,
    ) -> list[dict[str, Any]]:
        if mode == "chronology":
            index_field = "chronology_index"
        else:
            index_field = "release_index"

        return sorted(
            installments,
            key=lambda item: (
                item.get(index_field) is None,
                item.get(index_field)
                if item.get(index_field) is not None
                else 10**9,
                item.get("year") is None,
                item.get("year") if item.get("year") is not None else 10**9,
                cls._norm(item.get("title")).casefold(),
            ),
        )

    @classmethod
    def analyze(
        cls,
        *,
        main_node: dict[str, Any],
        classified_fields: dict[str, Any] | None,
        relationship_proposal: dict[str, Any] | None,
        universe_proposal: dict[str, Any] | None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        main_node = dict(main_node or {})
        classified_fields = dict(classified_fields or {})
        relationship_proposal = dict(relationship_proposal or {})
        universe_proposal = dict(universe_proposal or {})

        installments = cls._normalize_installments(
            main_node=main_node,
            classified_fields=classified_fields,
            relationship_proposal=relationship_proposal,
        )

        relation_edges = list(
            relationship_proposal.get("edges") or []
        )
        secure_relation = any(
            edge.get("edge_type") in cls.RELATION_TYPES
            for edge in relation_edges
        )

        primary = dict(
            classified_fields.get("primary_values") or {}
        )
        explicit_franchise = cls._norm(primary.get("franchise"))

        if (
            len(installments) < 2
            and not secure_relation
            and not explicit_franchise
        ):
            return {
                "schema_version": 1,
                "strategy": "franchise_collection_intelligence_v422",
                "franchise_count": 0,
                "installment_count": 0,
                "nodes": [],
                "edges": [],
                "release_order": [],
                "chronology_order": [],
                "warnings": [
                    "Keine sichere Medienreihe mit mindestens zwei Teilen "
                    "oder explizitem Franchise-Namen."
                ],
                "automatic_import": False,
                "requires_confirmation": True,
            }
        predecessor = dict(primary.get("predecessor") or {})

        franchise_title = (
            explicit_franchise
            or cls._clean_franchise_title(
                cls._norm(predecessor.get("title"))
            )
            or cls._clean_franchise_title(
                cls._norm(main_node.get("title"))
            )
        )
        franchise_key = cls._key("franchise", franchise_title)

        nodes: list[dict[str, Any]] = [{
            "key": franchise_key,
            "node_type": "franchise",
            "title": franchise_title,
            "confidence": 0.93,
            "metadata": {
                "franchise_intelligence": (
                    "franchise_collection_intelligence_v422"
                ),
                "explicit_franchise": bool(explicit_franchise),
            },
            "reason": (
                "Gemeinsame Medienreihe aus bestätigungspflichtigen "
                "Vorgänger-, Nachfolger- oder Sammlungsdaten."
            ),
            "source_id": source_id,
            "requires_confirmation": True,
        }]

        edges: list[dict[str, Any]] = []

        for item in installments:
            media_node = cls._media_node(
                title=item["title"],
                year=item.get("year"),
                node_type=item.get("node_type") or "media",
                source_id=source_id,
                reason="Teil der erkannten Medienreihe.",
            )
            media_node["metadata"].update({
                "role": item.get("role"),
                "release_index": item.get("release_index"),
                "chronology_index": item.get("chronology_index"),
            })
            nodes.append(media_node)
            edges.append({
                "edge_type": "installment_of",
                "source_node_key": media_node["key"],
                "target_node_key": franchise_key,
                "confidence": 0.94,
                "metadata": {
                    "franchise_intelligence": (
                        "franchise_collection_intelligence_v422"
                    ),
                    "role": item.get("role"),
                },
                "reason": "Medium gehört zur erkannten Reihe.",
                "source_id": source_id,
                "requires_confirmation": True,
            })

        # Preserve supported relation types.
        for edge in relation_edges:
            if edge.get("edge_type") not in cls.RELATION_TYPES:
                continue
            edges.append({
                **edge,
                "requires_confirmation": True,
                "automatic_import": False,
            })

        # Franchise can inherit one or more universe memberships.
        for edge in universe_proposal.get("edges") or []:
            if edge.get("edge_type") != "belongs_to":
                continue
            if edge.get("source_node_key") not in {
                main_node.get("key"),
                cls._key(
                    cls._norm(main_node.get("node_type") or "media"),
                    cls._norm(main_node.get("title")),
                    main_node.get("year")
                    or primary.get("release_year"),
                ),
            }:
                continue

            edges.append({
                "edge_type": "belongs_to",
                "source_node_key": franchise_key,
                "target_node_key": edge.get("target_node_key"),
                "confidence": 0.89,
                "metadata": {
                    "franchise_intelligence": (
                        "franchise_collection_intelligence_v422"
                    ),
                    "inherited_from_installment": (
                        edge.get("source_node_key")
                    ),
                },
                "reason": (
                    "Franchise-Zugehörigkeit aus einem Teil der Reihe "
                    "abgeleitet."
                ),
                "source_id": source_id,
                "requires_confirmation": True,
            })

        dedup_nodes: dict[str, dict[str, Any]] = {}
        for node in nodes:
            dedup_nodes[node["key"]] = node

        dedup_edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        for edge in edges:
            key = (
                edge.get("edge_type"),
                edge.get("source_node_key"),
                edge.get("target_node_key"),
            )
            dedup_edges[key] = edge

        release_order = [
            {
                "key": cls._key(
                    item.get("node_type") or "media",
                    item["title"],
                    item.get("year"),
                ),
                "title": item["title"],
                "year": item.get("year"),
                "index": index + 1,
            }
            for index, item in enumerate(
                cls._sort_installments(
                    installments,
                    mode="release",
                )
            )
        ]

        chronology_order = [
            {
                "key": cls._key(
                    item.get("node_type") or "media",
                    item["title"],
                    item.get("year"),
                ),
                "title": item["title"],
                "year": item.get("year"),
                "index": index + 1,
            }
            for index, item in enumerate(
                cls._sort_installments(
                    installments,
                    mode="chronology",
                )
            )
        ]

        return {
            "schema_version": 1,
            "strategy": "franchise_collection_intelligence_v422",
            "franchise_count": 1,
            "installment_count": sum(
                1
                for edge in dedup_edges.values()
                if edge.get("edge_type") == "installment_of"
            ),
            "franchise_key": franchise_key,
            "nodes": list(dedup_nodes.values()),
            "edges": list(dedup_edges.values()),
            "release_order": release_order,
            "chronology_order": chronology_order,
            "warnings": [],
            "automatic_import": False,
            "requires_confirmation": True,
        }
