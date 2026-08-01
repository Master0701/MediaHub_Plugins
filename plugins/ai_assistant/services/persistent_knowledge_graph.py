from __future__ import annotations
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PersistentKnowledgeGraphStore:
    def __init__(self, base_path: str | Path):
        base = Path(base_path)
        self.path = base.with_name("persistent_knowledge_graph.json")
        self.lock = threading.RLock()
        if not self.path.exists():
            self._write(self._empty())

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": self._now(),
            "nodes": {},
            "edges": {},
            "aliases": {},
            "history": [],
        }

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()

    def _write(self, data: dict[str, Any]) -> None:
        data["updated_at"] = self._now()
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.replace(self.path)

    @staticmethod
    def _edge_key(edge: dict[str, Any]) -> str:
        return "|".join([
            str(edge.get("edge_type") or ""),
            str(edge.get("source_node_key") or ""),
            str(edge.get("target_node_key") or ""),
        ])

    def preview_merge(self, proposal: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        nodes = data.get("nodes") or {}
        edges = data.get("edges") or {}
        new_nodes, existing_nodes, updated_nodes = [], [], []
        new_edges, existing_edges = [], []

        for node in proposal.get("nodes") or []:
            key = str(node.get("key") or "")
            old = nodes.get(key)
            if old is None:
                new_nodes.append(node)
            else:
                existing_nodes.append(key)
                if (
                    float(node.get("confidence") or 0)
                    > float(old.get("confidence") or 0)
                    or dict(node.get("metadata") or {})
                    != dict(old.get("metadata") or {})
                ):
                    updated_nodes.append({
                        "key": key,
                        "existing": old,
                        "proposed": node,
                    })

        for edge in proposal.get("edges") or []:
            key = self._edge_key(edge)
            (existing_edges if key in edges else new_edges).append(
                key if key in edges else edge
            )

        return {
            "new_nodes": new_nodes,
            "existing_nodes": existing_nodes,
            "updated_nodes": updated_nodes,
            "new_edges": new_edges,
            "existing_edges": existing_edges,
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def confirm_merge(
        self,
        proposal: dict[str, Any],
        confirmation_note: str = "",
    ) -> dict[str, Any]:
        with self.lock:
            data = self._read()
            nodes = dict(data.get("nodes") or {})
            edges = dict(data.get("edges") or {})
            aliases = dict(data.get("aliases") or {})
            added_nodes = updated_nodes = added_edges = 0

            for node in proposal.get("nodes") or []:
                key = str(node.get("key") or "")
                if not key:
                    continue
                value = dict(node)
                value["status"] = "confirmed"
                value["confirmed_at"] = self._now()
                old = nodes.get(key)
                if old is None:
                    nodes[key] = value
                    added_nodes += 1
                else:
                    merged = dict(old)
                    merged["metadata"] = {
                        **dict(old.get("metadata") or {}),
                        **dict(value.get("metadata") or {}),
                    }
                    if float(value.get("confidence") or 0) >= float(old.get("confidence") or 0):
                        merged.update(value)
                    nodes[key] = merged
                    updated_nodes += 1
                title = str(node.get("title") or "").strip()
                if title:
                    aliases[title.casefold()] = key

            for edge in proposal.get("edges") or []:
                key = self._edge_key(edge)
                value = dict(edge)
                value["status"] = "confirmed"
                value["confirmed_at"] = self._now()
                if key not in edges:
                    edges[key] = value
                    added_edges += 1

            history = list(data.get("history") or [])
            history.append({
                "id": uuid.uuid4().hex,
                "timestamp": self._now(),
                "action": "confirm_merge",
                "main_node_key": proposal.get("main_node_key"),
                "added_nodes": added_nodes,
                "updated_nodes": updated_nodes,
                "added_edges": added_edges,
                "note": confirmation_note,
            })

            data.update(
                nodes=nodes,
                edges=edges,
                aliases=aliases,
                history=history[-1000:],
            )
            self._write(data)
            return {
                "added_nodes": added_nodes,
                "updated_nodes": updated_nodes,
                "added_edges": added_edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "path": str(self.path.resolve()),
            }

    def resolve_node(self, title: str, node_type=None, year=None):
        wanted = " ".join(str(title or "").casefold().split())
        result = []
        for node in (self._read().get("nodes") or {}).values():
            current = " ".join(str(node.get("title") or "").casefold().split())
            if current != wanted:
                continue
            if node_type and node.get("node_type") != node_type:
                continue
            if year is not None and node.get("year") != year:
                continue
            result.append(node)
        return result

    def stats(self) -> dict[str, Any]:
        data = self._read()
        nodes = data.get("nodes") or {}
        edges = data.get("edges") or {}
        node_types, edge_types = {}, {}
        for node in nodes.values():
            kind = str(node.get("node_type") or "unknown")
            node_types[kind] = node_types.get(kind, 0) + 1
        for edge in edges.values():
            kind = str(edge.get("edge_type") or "unknown")
            edge_types[kind] = edge_types.get(kind, 0) + 1
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "history_count": len(data.get("history") or []),
            "path": str(self.path.resolve()),
            "updated_at": data.get("updated_at"),
        }
