from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True, slots=True)
class RenamePlanItem:
    index: int
    source_path: str
    target_path: str
    original_name: str
    proposed_name: str
    changed: bool
    blocked: bool
    highest_severity: str
    backend_id: str
    rule_sources: tuple[str, ...] = ()
    issues: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "original_name": self.original_name,
            "proposed_name": self.proposed_name,
            "changed": self.changed,
            "blocked": self.blocked,
            "highest_severity": self.highest_severity,
            "backend_id": self.backend_id,
            "rule_sources": list(self.rule_sources),
            "issues": [dict(issue) for issue in self.issues],
            "metadata": dict(self.metadata),
            "decision": dict(self.decision),
        }


@dataclass(frozen=True, slots=True)
class RenamePlan:
    plan_id: str
    created_at: str
    status: str
    backend_id: str
    items: tuple[RenamePlanItem, ...]
    blocking_count: int
    warning_count: int
    changed_count: int
    requires_confirmation: bool
    automatic_execution: bool
    executable: bool
    plan_hash: str
    preview_status: str
    conflicts: tuple[dict[str, Any], ...] = ()
    skipped: tuple[dict[str, Any], ...] = ()
    optional_integrations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "status": self.status,
            "backend_id": self.backend_id,
            "items": [item.to_dict() for item in self.items],
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "changed_count": self.changed_count,
            "requires_confirmation": self.requires_confirmation,
            "automatic_execution": self.automatic_execution,
            "executable": self.executable,
            "plan_hash": self.plan_hash,
            "preview_status": self.preview_status,
            "conflicts": [dict(value) for value in self.conflicts],
            "skipped": [dict(value) for value in self.skipped],
            "optional_integrations": dict(self.optional_integrations),
        }


class RenamePlanService:
    """
    Erzeugt einen unveränderlichen Ausführungsplan aus einer Vorschau.

    Der Plan ist die Sicherheitsgrenze zwischen Preview und einer bestätigten
    Transaktion. Sein SHA-256-Hash schützt die für die Ausführung relevanten
    Inhalte vor nachträglicher Veränderung.
    """

    @staticmethod
    def calculate_plan_hash(plan: RenamePlan) -> str:
        payload = {
            "backend_id": plan.backend_id,
            "items": [item.to_dict() for item in plan.items],
            "conflicts": [dict(value) for value in plan.conflicts],
            "skipped": [dict(value) for value in plan.skipped],
        }
        return hashlib.sha256(
            _stable_json(payload).encode("utf-8")
        ).hexdigest()

    @classmethod
    def verify_plan_hash(cls, plan: RenamePlan) -> bool:
        return cls.calculate_plan_hash(plan) == plan.plan_hash

    def create_from_preview(
        self,
        preview: dict[str, Any],
    ) -> RenamePlan:
        rows = list(preview.get("preview_rows") or [])
        media_items = list(preview.get("media_items") or [])

        media_by_path = {
            str(item.get("path") or ""): item
            for item in media_items
            if isinstance(item, dict)
        }

        items: list[RenamePlanItem] = []
        for position, row in enumerate(rows):
            source_path = str(row.get("source_path") or "")
            media_model = media_by_path.get(source_path, {})
            detection = dict(media_model.get("detection_data") or {})
            decision = dict(detection.get("decision") or {})

            items.append(
                RenamePlanItem(
                    index=int(row.get("index", position)),
                    source_path=source_path,
                    target_path=str(row.get("target_path") or ""),
                    original_name=str(row.get("original_name") or ""),
                    proposed_name=str(row.get("proposed_name") or ""),
                    changed=bool(row.get("changed")),
                    blocked=bool(row.get("blocked")),
                    highest_severity=str(
                        row.get("highest_severity") or "info"
                    ),
                    backend_id=str(
                        row.get("backend_id")
                        or preview.get("selected_backend")
                        or ""
                    ),
                    rule_sources=tuple(
                        str(value)
                        for value in row.get("rule_sources") or []
                    ),
                    issues=tuple(
                        dict(value)
                        for value in row.get("issues") or []
                        if isinstance(value, dict)
                    ),
                    metadata=dict(row.get("metadata") or {}),
                    decision=decision,
                )
            )

        blocking_count = sum(1 for item in items if item.blocked)
        warning_count = sum(
            1
            for item in items
            if item.highest_severity == "warning"
        )
        changed_count = sum(1 for item in items if item.changed)

        review_count = sum(
            1
            for item in items
            if bool(item.decision.get("review_required"))
        )

        executable = (
            bool(items)
            and changed_count > 0
            and blocking_count == 0
            and review_count == 0
        )

        status = (
            "blocked"
            if blocking_count
            else (
                "review_required"
                if review_count
                else (
                    "awaiting_confirmation"
                    if changed_count
                    else "no_changes"
                )
            )
        )

        hash_payload = {
            "backend_id": str(preview.get("selected_backend") or ""),
            "items": [item.to_dict() for item in items],
            "conflicts": list(preview.get("conflicts") or []),
            "skipped": list(preview.get("skipped") or []),
        }
        plan_hash = hashlib.sha256(
            _stable_json(hash_payload).encode("utf-8")
        ).hexdigest()

        return RenamePlan(
            plan_id=str(uuid4()),
            created_at=_utc_now(),
            status=status,
            backend_id=str(preview.get("selected_backend") or ""),
            items=tuple(items),
            blocking_count=blocking_count,
            warning_count=warning_count,
            changed_count=changed_count,
            requires_confirmation=True,
            automatic_execution=False,
            executable=executable,
            plan_hash=plan_hash,
            preview_status=str(preview.get("status") or ""),
            conflicts=tuple(
                dict(value)
                for value in preview.get("conflicts") or []
                if isinstance(value, dict)
            ),
            skipped=tuple(
                dict(value)
                for value in preview.get("skipped") or []
                if isinstance(value, dict)
            ),
            optional_integrations=dict(
                preview.get("optional_integrations") or {}
            ),
        )
