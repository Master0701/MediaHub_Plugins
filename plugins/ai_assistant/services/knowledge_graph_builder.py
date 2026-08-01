from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from typing import Any


class KnowledgeGraphBuilder:
    """Baut einen konsistenten Vorschlagsgraphen aus erkannten Knoten und Kanten."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _node_key(
        cls,
        node_type: str,
        title: str,
    ) -> str:
        return (
            f"{cls._norm(node_type).casefold()}:"
            f"{cls._norm(title).casefold()}"
        )

    @classmethod
    def _stable_id(
        cls,
        prefix: str,
        *parts: Any,
    ) -> str:
        payload = "|".join(cls._norm(part).casefold() for part in parts)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return f"{prefix}_{digest}"

    @classmethod
    def _canonical_node(
        cls,
        node: dict[str, Any],
    ) -> dict[str, Any] | None:
        node_type = cls._norm(
            node.get("node_type")
            or node.get("entity_type")
            or node.get("type")
        )
        title = cls._norm(
            node.get("title")
            or node.get("name")
            or node.get("label")
        )

        if not node_type or not title:
            return None

        key = cls._norm(node.get("key")) or cls._node_key(
            node_type,
            title,
        )

        confidence = float(node.get("confidence") or 0.0)
        metadata = dict(node.get("metadata") or {})

        return {
            "id": cls._stable_id("node", key),
            "key": key,
            "node_type": node_type,
            "title": title,
            "year": node.get("year"),
            "metadata": metadata,
            "confidence": round(confidence, 4),
            "reason": cls._norm(node.get("reason")),
            "source_id": node.get("source_id"),
            "status": "proposed",
            "requires_confirmation": True,
        }

    @classmethod
    def _canonical_edge(
        cls,
        edge: dict[str, Any],
    ) -> dict[str, Any] | None:
        edge_type = cls._norm(
            edge.get("edge_type")
            or edge.get("relation_type")
            or edge.get("type")
        )
        source_key = cls._norm(
            edge.get("source_node_key")
            or edge.get("source_key")
            or edge.get("from")
        )
        target_key = cls._norm(
            edge.get("target_node_key")
            or edge.get("target_key")
            or edge.get("to")
        )

        if not edge_type or not source_key or not target_key:
            return None

        return {
            "id": cls._stable_id(
                "edge",
                edge_type,
                source_key,
                target_key,
            ),
            "edge_type": edge_type,
            "source_node_id": edge.get("source_node_id"),
            "source_node_key": source_key,
            "target_node_id": edge.get("target_node_id"),
            "target_node_key": target_key,
            "metadata": dict(edge.get("metadata") or {}),
            "confidence": round(
                float(edge.get("confidence") or 0.0),
                4,
            ),
            "reason": cls._norm(edge.get("reason")),
            "evidence_id": edge.get("evidence_id"),
            "source_id": edge.get("source_id"),
            "status": "proposed",
            "requires_confirmation": True,
        }

    @classmethod
    def _legacy_key(
        cls,
        node_type: str,
        title: str,
        year: int | None = None,
    ) -> str:
        key = cls._node_key(node_type, title)
        if year is not None and node_type.casefold() in {
            "movie",
            "series",
            "event",
        }:
            key = f"{key}:{int(year)}"
        return key

    @classmethod
    def _legacy_node(
        cls,
        *,
        node_type: str,
        title: str,
        year: int | None,
        metadata: dict[str, Any] | None,
        confidence: float,
        reason: str,
        source_id: Any,
    ) -> dict[str, Any]:
        key = cls._legacy_key(node_type, title, year)
        return {
            "id": cls._stable_id("node", key),
            "key": key,
            "node_type": node_type,
            "title": title,
            "year": year,
            "metadata": dict(metadata or {}),
            "confidence": round(float(confidence), 4),
            "reason": reason,
            "source_id": source_id,
            "status": "proposed",
            "requires_confirmation": True,
        }

    @classmethod
    def _legacy_edge(
        cls,
        *,
        edge_type: str,
        source_node: dict[str, Any],
        target_node: dict[str, Any],
        confidence: float,
        reason: str,
        source_id: Any,
    ) -> dict[str, Any]:
        return {
            "id": cls._stable_id(
                "edge",
                edge_type,
                source_node["key"],
                target_node["key"],
            ),
            "edge_type": edge_type,
            "source_node_id": source_node["id"],
            "source_node_key": source_node["key"],
            "target_node_id": target_node["id"],
            "target_node_key": target_node["key"],
            "confidence": round(float(confidence), 4),
            "reason": reason,
            "source_id": source_id,
            "status": "proposed",
            "requires_confirmation": True,
        }

    @classmethod
    def _parse_legacy_metadata(
        cls,
        text: str,
    ) -> dict[str, Any]:
        source = cls._norm(text)
        metadata: dict[str, Any] = {}

        patterns = {
            "original_title": (
                r"\bOriginaltitel\s+(.+?)"
                r"(?=\s+Produktionsland\b|\s+Originalsprache\b|$)"
            ),
            "runtime_minutes": (
                r"\bLänge\s+(\d{1,4})\s+Minuten\b"
            ),
            "fsk": (
                r"\bFSK\s+(\d{1,2})\b"
            ),
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, source, flags=re.IGNORECASE)
            if not match:
                continue
            value: Any = match.group(1).strip()
            if field in {"runtime_minutes", "fsk"}:
                value = int(value)
            metadata[field] = value

        return metadata

    @classmethod
    def _parse_legacy_crew(
        cls,
        text: str,
    ) -> list[tuple[str, str]]:
        source = cls._norm(text)
        labels = (
            ("Regie", "directed_by"),
            ("Musik", "music_by"),
            ("Kamera", "cinematography_by"),
        )
        stop_labels = (
            "Drehbuch",
            "Produktion",
            "Musik",
            "Kamera",
            "Schnitt",
            "Besetzung",
            "Chronologie",
        )

        result: list[tuple[str, str]] = []
        for label, edge_type in labels:
            stop_pattern = "|".join(
                re.escape(item)
                for item in stop_labels
                if item != label
            )
            match = re.search(
                rf"\b{re.escape(label)}\s+"
                rf"(.+?)(?=\s+(?:{stop_pattern})\b|$)",
                source,
                flags=re.IGNORECASE,
            )
            if not match:
                continue

            name = cls._norm(match.group(1)).strip(" ,.;:")
            if name:
                result.append((edge_type, name))

        return result

    @classmethod
    def _legacy_groups(
        cls,
        *,
        source: dict[str, Any],
        parser_result: dict[str, Any] | None,
        semantic_result: dict[str, Any] | None,
        classified_fields: dict[str, Any] | None,
        scan_result: dict[str, Any] | None,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        str | None,
    ]:
        parser_result = dict(parser_result or {})
        semantic_result = dict(semantic_result or {})
        classified_fields = dict(classified_fields or {})
        scan_result = dict(scan_result or {})

        parser_fields = dict(
            (parser_result.get("result") or {}).get("fields")
            or parser_result.get("fields")
            or {}
        )
        primary_values = dict(
            classified_fields.get("primary_values")
            or {}
        )

        title = cls._norm(parser_fields.get("title"))
        media_type = cls._norm(
            parser_fields.get("media_type")
            or semantic_result.get("primary_entity_type")
            or "movie"
        )
        release_year = primary_values.get("release_year")
        confidence = float(
            semantic_result.get("primary_entity_confidence")
            or 0.84
        )
        source_id = source.get("id")

        if not title:
            return [], [], None

        text = str(scan_result.get("text_preview") or "")
        metadata = {
            "classified_fields": primary_values,
            **cls._parse_legacy_metadata(text),
        }

        main_node = cls._legacy_node(
            node_type=media_type,
            title=title,
            year=release_year,
            metadata=metadata,
            confidence=confidence,
            reason="Hauptobjekt der Quelle.",
            source_id=source_id,
        )

        nodes = [main_node]
        edges: list[dict[str, Any]] = []

        predecessor = primary_values.get("predecessor")
        if isinstance(predecessor, dict):
            predecessor_title = cls._norm(predecessor.get("title"))
            predecessor_year = predecessor.get("year")
            if predecessor_title:
                predecessor_node = cls._legacy_node(
                    node_type=media_type,
                    title=predecessor_title,
                    year=predecessor_year,
                    metadata={},
                    confidence=0.92,
                    reason="Explizit erkannter Vorgänger.",
                    source_id=source_id,
                )
                nodes.append(predecessor_node)
                edges.append(
                    cls._legacy_edge(
                        edge_type="sequel_of",
                        source_node=main_node,
                        target_node=predecessor_node,
                        confidence=0.92,
                        reason="Quelle nennt eine Fortsetzung.",
                        source_id=source_id,
                    )
                )

        universe = cls._norm(primary_values.get("universe"))
        universe_node = None
        if universe:
            universe_node = cls._legacy_node(
                node_type="universe",
                title=universe,
                year=None,
                metadata={},
                confidence=0.86,
                reason="Erkanntes Medienuniversum.",
                source_id=source_id,
            )
            nodes.append(universe_node)
            edges.append(
                cls._legacy_edge(
                    edge_type="belongs_to",
                    source_node=main_node,
                    target_node=universe_node,
                    confidence=0.86,
                    reason="Werk gehört zum Universum.",
                    source_id=source_id,
                )
            )

        transition_year = primary_values.get(
            "universe_transition_year"
        )
        if transition_year is not None and universe_node is not None:
            event_node = cls._legacy_node(
                node_type="event",
                title=f"Universumswechsel {int(transition_year)}",
                year=int(transition_year),
                metadata={"event_type": "universe_transition"},
                confidence=0.82,
                reason="Erkannter Universumswechsel.",
                source_id=source_id,
            )
            nodes.append(event_node)
            edges.append(
                cls._legacy_edge(
                    edge_type="ends_with",
                    source_node=universe_node,
                    target_node=event_node,
                    confidence=0.82,
                    reason="Universum endet mit Wechsel.",
                    source_id=source_id,
                )
            )

        for edge_type, person_name in cls._parse_legacy_crew(text):
            person_node = cls._legacy_node(
                node_type="person",
                title=person_name,
                year=None,
                metadata={},
                confidence=0.83,
                reason="Crew-Angabe.",
                source_id=source_id,
            )
            nodes.append(person_node)
            edges.append(
                cls._legacy_edge(
                    edge_type=edge_type,
                    source_node=main_node,
                    target_node=person_node,
                    confidence=0.83,
                    reason="Crew-Beziehung aus Quelle.",
                    source_id=source_id,
                )
            )

        return nodes, edges, main_node["key"]

    @classmethod
    def build(
        cls,
        *,
        node_groups: list[list[dict[str, Any]]] | None = None,
        edge_groups: list[list[dict[str, Any]]] | None = None,
        source: dict[str, Any] | None = None,
        parser_result: dict[str, Any] | None = None,
        semantic_result: dict[str, Any] | None = None,
        classified_fields: dict[str, Any] | None = None,
        scan_result: dict[str, Any] | None = None,
        knowledge_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        node_groups = list(node_groups or [])
        edge_groups = list(edge_groups or [])
        source = dict(source or {})

        knowledge_result = dict(knowledge_result or {})
        knowledge_nodes = list(
            knowledge_result.get("nodes")
            or knowledge_result.get("entity_nodes")
            or knowledge_result.get("entity_proposals")
            or []
        )
        knowledge_edges = list(
            knowledge_result.get("edges")
            or knowledge_result.get("relation_edges")
            or knowledge_result.get("relation_proposals")
            or []
        )

        nested_graph = knowledge_result.get("graph")
        if isinstance(nested_graph, dict):
            knowledge_nodes.extend(
                list(nested_graph.get("nodes") or [])
            )
            knowledge_edges.extend(
                list(nested_graph.get("edges") or [])
            )

        nested_proposal = knowledge_result.get("graph_proposal")
        if isinstance(nested_proposal, dict):
            knowledge_nodes.extend(
                list(nested_proposal.get("nodes") or [])
            )
            knowledge_edges.extend(
                list(nested_proposal.get("edges") or [])
            )

        if knowledge_nodes:
            node_groups.append(knowledge_nodes)
        if knowledge_edges:
            edge_groups.append(knowledge_edges)

        legacy_nodes, legacy_edges, legacy_main_node_key = (
            cls._legacy_groups(
                source=source,
                parser_result=parser_result,
                semantic_result=semantic_result,
                classified_fields=classified_fields,
                scan_result=scan_result,
            )
        )
        if legacy_nodes:
            node_groups.insert(0, legacy_nodes)
        if legacy_edges:
            edge_groups.insert(0, legacy_edges)

        node_index: dict[str, dict[str, Any]] = {}
        edge_index: dict[tuple[str, str, str], dict[str, Any]] = {}
        warnings: list[str] = []

        for group in node_groups:
            for raw_node in group or []:
                node = cls._canonical_node(dict(raw_node or {}))
                if node is None:
                    warnings.append("Ungültiger Knoten wurde übersprungen.")
                    continue

                key = node["key"]
                existing = node_index.get(key)

                if existing is None:
                    node_index[key] = node
                    continue

                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(node.get("confidence") or 0.0),
                )
                metadata = dict(existing.get("metadata") or {})
                metadata.update(dict(node.get("metadata") or {}))
                existing["metadata"] = metadata

                if not existing.get("reason") and node.get("reason"):
                    existing["reason"] = node["reason"]

        for group in edge_groups:
            for raw_edge in group or []:
                edge = cls._canonical_edge(dict(raw_edge or {}))
                if edge is None:
                    warnings.append("Ungültige Kante wurde übersprungen.")
                    continue

                edge_key = (
                    edge["edge_type"],
                    edge["source_node_key"],
                    edge["target_node_key"],
                )
                existing = edge_index.get(edge_key)

                if existing is None:
                    edge_index[edge_key] = edge
                    continue

                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(edge.get("confidence") or 0.0),
                )
                metadata = dict(existing.get("metadata") or {})
                metadata.update(dict(edge.get("metadata") or {}))
                existing["metadata"] = metadata

        missing_node_keys: set[str] = set()
        for edge in edge_index.values():
            for endpoint in (
                edge["source_node_key"],
                edge["target_node_key"],
            ):
                if endpoint not in node_index:
                    missing_node_keys.add(endpoint)

        for key in sorted(missing_node_keys):
            if ":" in key:
                node_type, title = key.split(":", 1)
            else:
                node_type, title = "unknown", key

            node_index[key] = {
                "id": cls._stable_id("node", key),
                "key": key,
                "node_type": node_type,
                "title": title,
                "metadata": {
                    "placeholder": True,
                    "created_from_edge_reference": True,
                },
                "confidence": 0.35,
                "reason": (
                    "Platzhalter aus einer vorhandenen Kantenreferenz."
                ),
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            }

        nodes = sorted(
            node_index.values(),
            key=lambda item: (
                item["node_type"],
                item["title"].casefold(),
            ),
        )
        edges = sorted(
            edge_index.values(),
            key=lambda item: (
                item["edge_type"],
                item["source_node_key"],
                item["target_node_key"],
            ),
        )

        node_types = Counter(
            item["node_type"]
            for item in nodes
        )
        edge_types = Counter(
            item["edge_type"]
            for item in edges
        )

        return {
            "schema_version": 1,
            "strategy": "knowledge_graph_builder_v402",
            "graph_id": uuid.uuid4().hex,
            "source": source,
            "source_id": source.get("id"),
            "main_node_key": legacy_main_node_key,
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "placeholder_node_count": sum(
                    1
                    for item in nodes
                    if item.get("metadata", {}).get("placeholder")
                ),
                "node_types": dict(sorted(node_types.items())),
                "edge_types": dict(sorted(edge_types.items())),
            },
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
