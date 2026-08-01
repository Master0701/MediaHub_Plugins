from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GraphProposalStore:
    """Persistente Warteschlange für bestätigbare Knowledge-Graph-Vorschläge."""

    def __init__(self, knowledge_database_path: str | Path):
        database_path = Path(knowledge_database_path)
        self.path = database_path.with_name(
            "knowledge_graph_proposals.json"
        )
        self._data = {"schema_version": 1, "proposals": []}
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
            self._data.setdefault("proposals", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _signature(proposal: dict[str, Any]) -> str:
        keys = (
            "kind",
            "source_id",
            "target_id",
            "relation_type",
            "entity_id",
            "group_name",
        )
        return "|".join(str(proposal.get(key) or "") for key in keys)

    def add_many(
        self,
        proposals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        signatures = {
            self._signature(item): item
            for item in self._data.get("proposals") or []
        }
        created = 0
        existing = 0

        for raw in proposals:
            proposal = dict(raw or {})
            signature = self._signature(proposal)
            previous = signatures.get(signature)
            if previous:
                existing += 1
                continue

            record = {
                **proposal,
                "id": uuid.uuid4().hex,
                "status": "pending",
                "created_at": self._now(),
                "updated_at": self._now(),
                "decision_note": None,
            }
            self._data["proposals"].append(record)
            signatures[signature] = record
            created += 1

        if created:
            self._save()

        return {
            "created_count": created,
            "existing_count": existing,
            "total_count": len(self._data["proposals"]),
        }

    def list(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        proposals = list(self._data.get("proposals") or [])
        if status is not None:
            proposals = [
                item
                for item in proposals
                if str(item.get("status")) == str(status)
            ]
        return proposals

    def get(self, proposal_id: str) -> dict[str, Any] | None:
        proposal_id = str(proposal_id)
        for item in self._data.get("proposals") or []:
            if str(item.get("id")) == proposal_id:
                return item
        return None

    def set_status(
        self,
        proposal_id: str,
        status: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        allowed = {"pending", "accepted", "rejected", "later"}
        if status not in allowed:
            raise ValueError(f"Ungültiger Vorschlagsstatus: {status}")

        proposal = self.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Vorschlag nicht gefunden: {proposal_id}")

        proposal["status"] = status
        proposal["updated_at"] = self._now()
        proposal["decision_note"] = note
        self._save()
        return dict(proposal)

    def status(self) -> dict[str, Any]:
        proposals = self.list()
        counts = {
            state: sum(
                1 for item in proposals
                if item.get("status") == state
            )
            for state in ("pending", "accepted", "rejected", "later")
        }
        return {
            "schema_version": 1,
            "path": str(self.path.resolve()),
            "total": len(proposals),
            **counts,
        }
