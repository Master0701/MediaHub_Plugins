from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MissingMediaHandoffService:
    """Erzeugt kontrollierte Übergaben und verarbeitet signalisierte Ergebnisse."""

    ALLOWED_RESULT_STATUSES = {
        "accepted",
        "not_found",
        "found",
        "resolved",
        "rejected",
        "later",
        "error",
    }

    def __init__(self, queue: Any, database_path: str | Path):
        self.queue = queue
        database = Path(database_path)
        self.log_path = database.with_name(
            "missing_media_handoff_log.json"
        )
        self._log = {
            "schema_version": 1,
            "handoffs": [],
            "results": [],
        }
        self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> None:
        if not self.log_path.exists():
            return
        try:
            data = json.loads(self.log_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, dict):
            self._log = data
            self._log.setdefault("schema_version", 1)
            self._log.setdefault("handoffs", [])
            self._log.setdefault("results", [])

    def _save(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.log_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._log, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.log_path)

    def create_handoff(
        self,
        *,
        target_plugin: str,
        statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        target_plugin = str(target_plugin or "").strip()
        if not target_plugin:
            raise ValueError("Ein Ziel-Plugin muss angegeben werden.")

        selected = set(statuses or ["pending", "wanted", "later"])
        items = [
            dict(item)
            for item in self.queue.list()
            if item.get("status") in selected
        ]

        handoff_id = uuid.uuid4().hex
        payload = {
            "schema_version": 1,
            "handoff_id": handoff_id,
            "created_at": self._now(),
            "producer": "mediahub.ai_assistant",
            "producer_version": "2.4.3",
            "target_plugin": target_plugin,
            "kind": "missing_media_handoff",
            "allowed_actions": [
                "report_status",
                "report_found",
                "report_not_found",
                "report_error",
            ],
            "items": items,
            "safety": {
                "automatic_download": False,
                "automatic_search": False,
                "automatic_file_change": False,
                "queue_write_access": False,
            },
        }

        self._log["handoffs"].append(
            {
                "handoff_id": handoff_id,
                "target_plugin": target_plugin,
                "created_at": payload["created_at"],
                "item_ids": [item.get("id") for item in items],
                "item_count": len(items),
            }
        )
        self._save()
        return payload

    def apply_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        handoff_id = str(result.get("handoff_id") or "").strip()
        item_id = str(result.get("item_id") or "").strip()
        status = str(result.get("status") or "").strip()

        if not handoff_id:
            raise ValueError("handoff_id fehlt.")
        if not item_id:
            raise ValueError("item_id fehlt.")
        if status not in self.ALLOWED_RESULT_STATUSES:
            raise ValueError(f"Ungültiger Ergebnisstatus: {status}")

        known_handoff = next(
            (
                item
                for item in self._log.get("handoffs") or []
                if item.get("handoff_id") == handoff_id
            ),
            None,
        )
        if known_handoff is None:
            raise KeyError(f"Unbekannte Übergabe: {handoff_id}")

        if item_id not in set(known_handoff.get("item_ids") or []):
            raise ValueError(
                "Der Eintrag gehört nicht zu dieser Übergabe."
            )

        queue_status = {
            "accepted": "wanted",
            "found": "wanted",
            "not_found": "later",
            "resolved": "resolved",
            "rejected": "rejected",
            "later": "later",
            "error": "later",
        }[status]

        note = str(result.get("note") or "").strip() or None
        queue_result = self.queue.set_status(
            item_id,
            queue_status,
            note,
        )

        result_record = {
            "id": uuid.uuid4().hex,
            "received_at": self._now(),
            "handoff_id": handoff_id,
            "item_id": item_id,
            "status": status,
            "queue_status": queue_status,
            "source_plugin": result.get("source_plugin"),
            "note": note,
        }
        self._log["results"].append(result_record)
        self._save()

        return {
            "accepted": True,
            "queue_item": queue_result,
            "result": result_record,
        }

    def status(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "log_path": str(self.log_path.resolve()),
            "handoff_count": len(self._log.get("handoffs") or []),
            "result_count": len(self._log.get("results") or []),
        }
