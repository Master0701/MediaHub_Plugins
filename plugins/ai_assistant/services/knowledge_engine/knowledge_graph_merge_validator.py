from __future__ import annotations

from typing import Any


class KnowledgeGraphMergeValidator:
    """Vereinigt Graph-Teilresultate und markiert Konflikte."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _node_signature(
        cls,
        node: dict[str, Any],
    ) -> tuple[str, str]:
        return (
            cls._norm(node.get("node_type")).casefold(),
            cls._norm(node.get("key")).casefold(),
        )

    @classmethod
    def _edge_signature(
        cls,
        edge: dict[str, Any],
    ) -> tuple[str, str, str]:
        return (
            cls._norm(edge.get("edge_type")).casefold(),
            cls._norm(edge.get("source_node_key")).casefold(),
            cls._norm(edge.get("target_node_key")).casefold(),
        )

    @classmethod
    def _merge_metadata(
        cls,
        first: dict[str, Any] | None,
        second: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result = dict(first or {})
        for key, value in dict(second or {}).items():
            if key not in result:
                result[key] = value
                continue

            existing = result[key]
            if existing == value:
                continue

            if isinstance(existing, list):
                merged = list(existing)
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if item not in merged:
                        merged.append(item)
                result[key] = merged
                continue

            if isinstance(value, list):
                merged = [existing]
                for item in value:
                    if item not in merged:
                        merged.append(item)
                result[key] = merged
                continue

            result[key] = [existing, value]

        return result

    @classmethod
    def _merge_sources(
        cls,
        first: Any,
        second: Any,
    ) -> list[str]:
        values: list[str] = []
        for raw in (first, second):
            if raw is None:
                continue
            candidates = raw if isinstance(raw, list) else [raw]
            for item in candidates:
                text = cls._norm(item)
                if text and text not in values:
                    values.append(text)
        return values

    @classmethod
    def _merge_node(
        cls,
        current: dict[str, Any],
        incoming: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = dict(current)

        for field in ("title", "year", "node_type"):
            old = result.get(field)
            new = incoming.get(field)
            if old in (None, "") and new not in (None, ""):
                result[field] = new
            elif (
                old not in (None, "")
                and new not in (None, "")
                and old != new
            ):
                conflicts.append({
                    "kind": "node_field_conflict",
                    "key": result.get("key"),
                    "field": field,
                    "values": [old, new],
                    "requires_confirmation": True,
                })

        result["confidence"] = max(
            float(result.get("confidence") or 0.0),
            float(incoming.get("confidence") or 0.0),
        )
        result["metadata"] = cls._merge_metadata(
            result.get("metadata"),
            incoming.get("metadata"),
        )
        result["source_ids"] = cls._merge_sources(
            result.get("source_ids") or result.get("source_id"),
            incoming.get("source_ids") or incoming.get("source_id"),
        )
        result.pop("source_id", None)
        result["requires_confirmation"] = True
        result["automatic_import"] = False
        return result

    @classmethod
    def _merge_edge(
        cls,
        current: dict[str, Any],
        incoming: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(current)
        result["confidence"] = max(
            float(result.get("confidence") or 0.0),
            float(incoming.get("confidence") or 0.0),
        )
        result["metadata"] = cls._merge_metadata(
            result.get("metadata"),
            incoming.get("metadata"),
        )
        result["source_ids"] = cls._merge_sources(
            result.get("source_ids") or result.get("source_id"),
            incoming.get("source_ids") or incoming.get("source_id"),
        )
        result.pop("source_id", None)
        result["requires_confirmation"] = True
        result["automatic_import"] = False
        return result

    @classmethod
    def merge(
        cls,
        *,
        graph_groups: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        node_map: dict[tuple[str, str], dict[str, Any]] = {}
        edge_map: dict[
            tuple[str, str, str],
            dict[str, Any],
        ] = {}
        conflicts: list[dict[str, Any]] = []
        warnings: list[str] = []
        group_count = 0

        for group in graph_groups or []:
            if not isinstance(group, dict):
                warnings.append(
                    "Ungültige Graph-Gruppe wurde übersprungen."
                )
                continue

            group_count += 1

            for node in group.get("nodes") or []:
                if not isinstance(node, dict):
                    warnings.append(
                        "Ungültiger Knoten wurde übersprungen."
                    )
                    continue

                key = cls._norm(node.get("key"))
                node_type = cls._norm(node.get("node_type"))
                if not key or not node_type:
                    warnings.append(
                        "Knoten ohne key oder node_type wurde übersprungen."
                    )
                    continue

                signature = cls._node_signature(node)
                prepared = {
                    **node,
                    "requires_confirmation": True,
                    "automatic_import": False,
                }

                existing = node_map.get(signature)
                if existing is None:
                    source_ids = cls._merge_sources(
                        prepared.get("source_ids")
                        or prepared.get("source_id"),
                        None,
                    )
                    prepared["source_ids"] = source_ids
                    prepared.pop("source_id", None)
                    node_map[signature] = prepared
                else:
                    node_map[signature] = cls._merge_node(
                        existing,
                        prepared,
                        conflicts,
                    )

            for edge in group.get("edges") or []:
                if not isinstance(edge, dict):
                    warnings.append(
                        "Ungültige Kante wurde übersprungen."
                    )
                    continue

                if not all(
                    cls._norm(edge.get(field))
                    for field in (
                        "edge_type",
                        "source_node_key",
                        "target_node_key",
                    )
                ):
                    warnings.append(
                        "Unvollständige Kante wurde übersprungen."
                    )
                    continue

                signature = cls._edge_signature(edge)
                prepared = {
                    **edge,
                    "requires_confirmation": True,
                    "automatic_import": False,
                }

                existing = edge_map.get(signature)
                if existing is None:
                    source_ids = cls._merge_sources(
                        prepared.get("source_ids")
                        or prepared.get("source_id"),
                        None,
                    )
                    prepared["source_ids"] = source_ids
                    prepared.pop("source_id", None)
                    edge_map[signature] = prepared
                else:
                    edge_map[signature] = cls._merge_edge(
                        existing,
                        prepared,
                    )

        node_keys = {
            cls._norm(node.get("key")).casefold()
            for node in node_map.values()
        }

        dangling_edges: list[dict[str, Any]] = []
        for edge in edge_map.values():
            source_key = cls._norm(
                edge.get("source_node_key")
            ).casefold()
            target_key = cls._norm(
                edge.get("target_node_key")
            ).casefold()

            missing: list[str] = []
            if source_key not in node_keys:
                missing.append("source")
            if target_key not in node_keys:
                missing.append("target")

            if missing:
                dangling_edges.append({
                    "edge_type": edge.get("edge_type"),
                    "source_node_key": edge.get("source_node_key"),
                    "target_node_key": edge.get("target_node_key"),
                    "missing": missing,
                    "requires_confirmation": True,
                })

        return {
            "schema_version": 1,
            "strategy": "knowledge_graph_merge_validator_v430",
            "group_count": group_count,
            "node_count": len(node_map),
            "edge_count": len(edge_map),
            "conflict_count": len(conflicts),
            "dangling_edge_count": len(dangling_edges),
            "nodes": list(node_map.values()),
            "edges": list(edge_map.values()),
            "conflicts": conflicts,
            "dangling_edges": dangling_edges,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
