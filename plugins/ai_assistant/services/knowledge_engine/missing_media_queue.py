from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MissingMediaQueue:
    """Persistente Aufgabenliste für erkannte fehlende Medien."""

    def __init__(self, knowledge_database_path: str | Path):
        database_path = Path(knowledge_database_path)
        self.path = database_path.with_name("missing_media_queue.json")
        self._data = {"schema_version": 1, "items": []}
        self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(loaded, dict):
            self._data = loaded
            self._data.setdefault("schema_version", 1)
            self._data.setdefault("items", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _signature(item: dict[str, Any]) -> str:
        return "|".join(
            (
                str(item.get("group_type") or ""),
                str(item.get("group_name") or "").casefold(),
                str(item.get("title") or "").casefold(),
                str(item.get("year") or ""),
                str(item.get("media_type") or ""),
            )
        )

    def add_from_completeness(
        self,
        completeness: dict[str, Any],
    ) -> dict[str, Any]:
        known = {
            self._signature(item): item
            for item in self._data.get("items") or []
        }
        created = 0
        existing = 0

        for group in completeness.get("groups") or []:
            for missing in group.get("missing") or []:
                candidate = {
                    "group_type": group.get("group_type"),
                    "group_name": group.get("group_name"),
                    "title": missing.get("title"),
                    "year": missing.get("year"),
                    "media_type": missing.get("media_type"),
                }
                signature = self._signature(candidate)
                if signature in known:
                    existing += 1
                    continue

                record = {
                    **candidate,
                    "id": uuid.uuid4().hex,
                    "status": "pending",
                    "created_at": self._now(),
                    "updated_at": self._now(),
                    "note": None,
                    "automatic_action": False,
                }
                self._data["items"].append(record)
                known[signature] = record
                created += 1

        if created:
            self._save()

        return {
            "created_count": created,
            "existing_count": existing,
            "total_count": len(self._data["items"]),
        }

    def list(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        items = list(self._data.get("items") or [])
        if status is not None:
            items = [
                item
                for item in items
                if str(item.get("status")) == str(status)
            ]
        return items

    def get(self, item_id: str) -> dict[str, Any] | None:
        item_id = str(item_id)
        for item in self._data.get("items") or []:
            if str(item.get("id")) == item_id:
                return item
        return None

    def set_status(
        self,
        item_id: str,
        status: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        allowed = {
            "pending",
            "wanted",
            "rejected",
            "later",
            "resolved",
        }
        if status not in allowed:
            raise ValueError(f"Ungültiger Status: {status}")

        item = self.get(item_id)
        if item is None:
            raise KeyError(f"Eintrag nicht gefunden: {item_id}")

        item["status"] = status
        item["updated_at"] = self._now()
        item["note"] = note
        self._save()
        return dict(item)

    @staticmethod
    def _normalized_title(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def reconcile_entity(
        self,
        entity: dict[str, Any],
    ) -> dict[str, Any]:
        """Markiert passende offene Einträge als vorhanden."""
        title = self._normalized_title(entity.get("title"))
        aliases = {
            self._normalized_title(alias)
            for alias in entity.get("aliases") or []
            if self._normalized_title(alias)
        }
        titles = {title, *aliases}
        year = entity.get("year")
        media_type = str(entity.get("media_type") or "").strip()

        resolved = []
        for item in self._data.get("items") or []:
            if item.get("status") in {"resolved", "rejected"}:
                continue

            item_title = self._normalized_title(item.get("title"))
            if item_title not in titles:
                continue

            item_year = item.get("year")
            if (
                item_year is not None
                and year is not None
                and int(item_year) != int(year)
            ):
                continue

            item_type = str(item.get("media_type") or "").strip()
            if item_type and media_type and item_type != media_type:
                continue

            item["status"] = "resolved"
            item["updated_at"] = self._now()
            item["note"] = (
                "Automatisch als vorhanden markiert, weil eine bestätigte "
                "Knowledge-Graph-Entität gefunden wurde."
            )
            item["resolved_entity_id"] = entity.get("id")
            resolved.append(dict(item))

        if resolved:
            self._save()

        return {
            "resolved_count": len(resolved),
            "resolved_items": resolved,
        }

    def reconcile_entities(
        self,
        entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        results = [
            self.reconcile_entity(entity)
            for entity in entities
        ]
        resolved = [
            item
            for result in results
            for item in result.get("resolved_items") or []
        ]
        return {
            "processed_entity_count": len(entities),
            "resolved_count": len(resolved),
            "resolved_items": resolved,
        }

    def status(self) -> dict[str, Any]:
        items = self.list()
        counts = {
            state: sum(
                1
                for item in items
                if item.get("status") == state
            )
            for state in (
                "pending",
                "wanted",
                "rejected",
                "later",
                "resolved",
            )
        }
        return {
            "schema_version": 1,
            "path": str(self.path.resolve()),
            "total": len(items),
            **counts,
        }
