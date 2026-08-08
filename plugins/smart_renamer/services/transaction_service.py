from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.rename_plan import RenamePlan


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ConfirmationReceipt:
    plan_id: str
    plan_hash: str
    confirmed: bool
    confirmed_at: str
    confirmation_token: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "confirmed": self.confirmed,
            "confirmed_at": self.confirmed_at,
            "confirmation_token": self.confirmation_token,
            "execution_unlocked": False,
        }


class RenameTransactionService:
    """
    Bereitet Bestätigung und Rollback-Daten vor.

    v0.5.0 besitzt absichtlich KEINEN Dateisystem-Commit. Auch ein bestätigter
    Plan wird nicht ausgeführt.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.transaction_dir = (
            self.base_dir
            / "config"
            / "smart_renamer_transactions"
        )

    def prepare_rollback_manifest(
        self,
        plan: RenamePlan,
    ) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        for item in plan.items:
            if not item.changed:
                continue

            source = Path(item.source_path)
            source_stat = None
            try:
                source_stat = source.stat()
            except OSError:
                pass

            entries.append(
                {
                    "index": item.index,
                    "source_path": item.source_path,
                    "target_path": item.target_path,
                    "original_name": item.original_name,
                    "proposed_name": item.proposed_name,
                    "item_type": (
                        "folder"
                        if source.is_dir()
                        else "file"
                    ),
                    "source_exists_at_plan_time": source.exists(),
                    "source_size_at_plan_time": (
                        source_stat.st_size
                        if source_stat and source.is_file()
                        else None
                    ),
                    "source_mtime_at_plan_time": (
                        source_stat.st_mtime
                        if source_stat
                        else None
                    ),
                    "state": "planned",
                }
            )

        return {
            "schema_version": 1,
            "plan_id": plan.plan_id,
            "plan_hash": plan.plan_hash,
            "created_at": _utc_now(),
            "status": "prepared",
            "execution_performed": False,
            "entries": entries,
        }

    def save_prepared_transaction(
        self,
        plan: RenamePlan,
    ) -> dict[str, str]:
        """
        Speichert ausschließlich Plan + Rollback-Vorbereitung im Config-Bereich.
        Dateien/Ordner der Medienbibliothek werden nicht verändert.
        """
        self.transaction_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        folder = self.transaction_dir / plan.plan_id
        folder.mkdir(parents=True, exist_ok=False)

        plan_path = folder / "rename_plan.json"
        rollback_path = folder / "rollback.json"

        plan_path.write_text(
            json.dumps(
                plan.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        rollback_path.write_text(
            json.dumps(
                self.prepare_rollback_manifest(plan),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "transaction_dir": str(folder),
            "plan_path": str(plan_path),
            "rollback_path": str(rollback_path),
        }

    def confirm(
        self,
        plan: RenamePlan,
        *,
        user_confirmed: bool,
    ) -> ConfirmationReceipt:
        if not user_confirmed:
            raise ValueError(
                "Der Ausführungsplan wurde nicht ausdrücklich bestätigt."
            )
        if not plan.executable:
            raise RuntimeError(
                "Der Plan ist wegen Konflikten, Review oder fehlenden "
                "Änderungen nicht freigabefähig."
            )

        confirmed_at = _utc_now()
        token_source = (
            f"{plan.plan_id}|{plan.plan_hash}|{confirmed_at}|confirmed"
        )
        token = hashlib.sha256(
            token_source.encode("utf-8")
        ).hexdigest()

        return ConfirmationReceipt(
            plan_id=plan.plan_id,
            plan_hash=plan.plan_hash,
            confirmed=True,
            confirmed_at=confirmed_at,
            confirmation_token=token,
        )

    def execute(self, *args, **kwargs):
        raise RuntimeError(
            "Smart Renamer v0.5.0 bereitet Transaktionen nur vor. "
            "Dateisystem-Ausführung ist weiterhin gesperrt."
        )
