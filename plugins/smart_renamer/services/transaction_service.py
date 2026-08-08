from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.rename_plan import RenamePlan, RenamePlanService


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
            "execution_unlocked": self.confirmed,
        }


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    ok: bool
    plan_id: str
    status: str
    renamed_count: int
    rolled_back_count: int
    error: str = ""
    transaction_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plan_id": self.plan_id,
            "status": self.status,
            "renamed_count": self.renamed_count,
            "rolled_back_count": self.rolled_back_count,
            "error": self.error,
            "transaction_dir": self.transaction_dir,
        }


class RenameTransactionService:
    """
    Sichere, bestätigungspflichtige Rename-Transaktion.

    Sicherheitsgrenzen:
    - nur konfliktfreie/executable RenamePlans
    - unveränderter Planhash
    - explizite, in dieser Service-Instanz erzeugte ConfirmationReceipt
    - unmittelbar vor Commit erneute Dateisystemprüfung
    - keine Überschreibung vorhandener Ziele
    - automatischer Rollback aller bereits ausgeführten Schritte bei Fehler
    - persistentes Transaktionsjournal
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.transaction_dir = (
            self.base_dir
            / "config"
            / "smart_renamer_transactions"
        )
        self._confirmations: dict[str, tuple[str, str]] = {}

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
            "schema_version": 2,
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
        self.transaction_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        folder = self.transaction_dir / plan.plan_id
        folder.mkdir(parents=True, exist_ok=False)

        plan_path = folder / "rename_plan.json"
        rollback_path = folder / "rollback.json"
        journal_path = folder / "journal.json"

        self._write_json(plan_path, plan.to_dict())
        self._write_json(
            rollback_path,
            self.prepare_rollback_manifest(plan),
        )
        self._write_json(
            journal_path,
            {
                "schema_version": 1,
                "plan_id": plan.plan_id,
                "plan_hash": plan.plan_hash,
                "status": "prepared",
                "execution_performed": False,
                "events": [
                    {
                        "at": _utc_now(),
                        "event": "transaction_prepared",
                    }
                ],
            },
        )

        return {
            "transaction_dir": str(folder),
            "plan_path": str(plan_path),
            "rollback_path": str(rollback_path),
            "journal_path": str(journal_path),
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
        self._validate_plan_for_execution(plan)

        confirmed_at = _utc_now()
        token_source = (
            f"{plan.plan_id}|{plan.plan_hash}|{confirmed_at}|confirmed"
        )
        token = hashlib.sha256(
            token_source.encode("utf-8")
        ).hexdigest()

        self._confirmations[token] = (
            plan.plan_id,
            plan.plan_hash,
        )

        return ConfirmationReceipt(
            plan_id=plan.plan_id,
            plan_hash=plan.plan_hash,
            confirmed=True,
            confirmed_at=confirmed_at,
            confirmation_token=token,
        )

    def execute(
        self,
        plan: RenamePlan,
        *,
        confirmation_token: str,
    ) -> ExecutionResult:
        """
        Führt ausschließlich einen zuvor bestätigten und erneut validierten Plan
        aus. Bei jedem Fehler werden alle bereits ausgeführten Renames in
        umgekehrter Reihenfolge zurückgerollt.
        """
        self._validate_confirmation(plan, confirmation_token)
        self._validate_plan_for_execution(plan)
        self._preflight_filesystem(plan)

        folder = self._ensure_transaction_folder(plan)
        journal_path = folder / "journal.json"
        rollback_path = folder / "rollback.json"

        if not rollback_path.is_file():
            self._write_json(
                rollback_path,
                self.prepare_rollback_manifest(plan),
            )

        completed: list[tuple[Path, Path]] = []
        self._append_journal(
            journal_path,
            plan,
            "execution_started",
            status="running",
            execution_performed=True,
        )

        try:
            for item in plan.items:
                if not item.changed:
                    continue

                source = Path(item.source_path)
                target = Path(item.target_path)

                # Noch einmal direkt vor JEDEM einzelnen Rename prüfen.
                if not source.exists():
                    raise RuntimeError(
                        f"Quelle fehlt unmittelbar vor Rename: {source}"
                    )
                if target.exists():
                    raise RuntimeError(
                        f"Ziel existiert unmittelbar vor Rename: {target}"
                    )
                if source.parent.resolve() != target.parent.resolve():
                    raise RuntimeError(
                        "v0.5.2 erlaubt nur Umbenennungen innerhalb "
                        "desselben Ordners."
                    )

                source.rename(target)
                completed.append((source, target))
                self._mark_rollback_entry(
                    rollback_path,
                    item.index,
                    "renamed",
                )
                self._append_journal(
                    journal_path,
                    plan,
                    "item_renamed",
                    status="running",
                    details={
                        "index": item.index,
                        "source_path": str(source),
                        "target_path": str(target),
                    },
                )

        except Exception as exc:
            rolled_back, rollback_error = self._rollback_completed(
                completed,
                rollback_path,
                journal_path,
                plan,
            )
            status = (
                "rolled_back"
                if not rollback_error
                else "rollback_failed"
            )
            self._append_journal(
                journal_path,
                plan,
                "execution_failed",
                status=status,
                details={
                    "error": str(exc),
                    "rollback_error": rollback_error,
                },
            )
            self._confirmations.pop(confirmation_token, None)
            return ExecutionResult(
                ok=False,
                plan_id=plan.plan_id,
                status=status,
                renamed_count=len(completed),
                rolled_back_count=rolled_back,
                error=(
                    str(exc)
                    if not rollback_error
                    else f"{exc}; Rollbackfehler: {rollback_error}"
                ),
                transaction_dir=str(folder),
            )

        self._append_journal(
            journal_path,
            plan,
            "execution_completed",
            status="completed",
            execution_performed=True,
        )
        self._set_rollback_status(
            rollback_path,
            status="completed",
            execution_performed=True,
        )
        self._confirmations.pop(confirmation_token, None)

        return ExecutionResult(
            ok=True,
            plan_id=plan.plan_id,
            status="completed",
            renamed_count=len(completed),
            rolled_back_count=0,
            transaction_dir=str(folder),
        )

    def rollback_transaction(
        self,
        plan: RenamePlan,
    ) -> ExecutionResult:
        """
        Manueller Undo für eine erfolgreich abgeschlossene Transaktion.

        Es wird niemals überschrieben: existiert der ursprüngliche Quellpfad,
        wird der Rollback abgebrochen.
        """
        folder = self.transaction_dir / plan.plan_id
        rollback_path = folder / "rollback.json"
        journal_path = folder / "journal.json"

        if not rollback_path.is_file():
            raise FileNotFoundError(
                f"Rollback-Manifest fehlt: {rollback_path}"
            )

        data = json.loads(
            rollback_path.read_text(encoding="utf-8")
        )
        entries = list(data.get("entries") or [])

        restored = 0
        try:
            for entry in reversed(entries):
                if entry.get("state") != "renamed":
                    continue

                source = Path(str(entry["source_path"]))
                target = Path(str(entry["target_path"]))

                if source.exists():
                    raise RuntimeError(
                        f"Rollback-Ziel ist bereits belegt: {source}"
                    )
                if not target.exists():
                    raise RuntimeError(
                        f"Umbenannte Datei fehlt für Rollback: {target}"
                    )

                target.rename(source)
                entry["state"] = "rolled_back"
                restored += 1
                self._write_json(rollback_path, data)

            data["status"] = "rolled_back"
            data["execution_performed"] = True
            self._write_json(rollback_path, data)
            self._append_journal(
                journal_path,
                plan,
                "manual_rollback_completed",
                status="rolled_back",
                execution_performed=True,
            )
            return ExecutionResult(
                ok=True,
                plan_id=plan.plan_id,
                status="rolled_back",
                renamed_count=0,
                rolled_back_count=restored,
                transaction_dir=str(folder),
            )
        except Exception as exc:
            self._append_journal(
                journal_path,
                plan,
                "manual_rollback_failed",
                status="rollback_failed",
                details={"error": str(exc)},
            )
            return ExecutionResult(
                ok=False,
                plan_id=plan.plan_id,
                status="rollback_failed",
                renamed_count=0,
                rolled_back_count=restored,
                error=str(exc),
                transaction_dir=str(folder),
            )

    def _validate_plan_for_execution(
        self,
        plan: RenamePlan,
    ) -> None:
        if not plan.executable:
            raise RuntimeError(
                "Der Plan ist wegen Konflikten, Review oder fehlenden "
                "Änderungen nicht ausführbar."
            )
        if not RenamePlanService.verify_plan_hash(plan):
            raise RuntimeError(
                "Planhash stimmt nicht. Der Plan wurde verändert oder ist "
                "beschädigt."
            )

    def _validate_confirmation(
        self,
        plan: RenamePlan,
        token: str,
    ) -> None:
        stored = self._confirmations.get(str(token))
        if stored is None:
            raise PermissionError(
                "Keine gültige Bestätigung für diese Transaktion."
            )
        if stored != (plan.plan_id, plan.plan_hash):
            raise PermissionError(
                "Bestätigung gehört nicht zu diesem unveränderten Plan."
            )

    def _preflight_filesystem(
        self,
        plan: RenamePlan,
    ) -> None:
        targets: set[str] = set()

        for item in plan.items:
            if not item.changed:
                continue

            source = Path(item.source_path)
            target = Path(item.target_path)

            if not source.exists():
                raise RuntimeError(
                    f"Quelle existiert nicht mehr: {source}"
                )
            if source.resolve() == target.resolve():
                raise RuntimeError(
                    f"Quelle und Ziel sind identisch: {source}"
                )
            if source.parent.resolve() != target.parent.resolve():
                raise RuntimeError(
                    "v0.5.2 erlaubt nur Umbenennungen innerhalb "
                    "desselben Ordners."
                )
            if target.exists():
                raise RuntimeError(
                    f"Ziel existiert bereits: {target}"
                )

            target_key = str(target.resolve()).casefold()
            if target_key in targets:
                raise RuntimeError(
                    f"Doppelter Zielpfad im Plan: {target}"
                )
            targets.add(target_key)

    def _ensure_transaction_folder(
        self,
        plan: RenamePlan,
    ) -> Path:
        self.transaction_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        folder = self.transaction_dir / plan.plan_id
        folder.mkdir(parents=True, exist_ok=True)

        plan_path = folder / "rename_plan.json"
        if not plan_path.is_file():
            self._write_json(plan_path, plan.to_dict())

        journal_path = folder / "journal.json"
        if not journal_path.is_file():
            self._write_json(
                journal_path,
                {
                    "schema_version": 1,
                    "plan_id": plan.plan_id,
                    "plan_hash": plan.plan_hash,
                    "status": "prepared",
                    "execution_performed": False,
                    "events": [],
                },
            )

        return folder

    def _rollback_completed(
        self,
        completed: list[tuple[Path, Path]],
        rollback_path: Path,
        journal_path: Path,
        plan: RenamePlan,
    ) -> tuple[int, str]:
        count = 0
        errors: list[str] = []

        for source, target in reversed(completed):
            try:
                if source.exists():
                    raise RuntimeError(
                        f"Ursprünglicher Pfad bereits belegt: {source}"
                    )
                if not target.exists():
                    raise RuntimeError(
                        f"Rollback-Quelle fehlt: {target}"
                    )
                target.rename(source)
                count += 1
                self._mark_rollback_by_paths(
                    rollback_path,
                    str(source),
                    str(target),
                    "rolled_back",
                )
                self._append_journal(
                    journal_path,
                    plan,
                    "item_rolled_back",
                    status="rolling_back",
                    details={
                        "source_path": str(source),
                        "target_path": str(target),
                    },
                )
            except Exception as exc:
                errors.append(str(exc))

        self._set_rollback_status(
            rollback_path,
            status=(
                "rolled_back"
                if not errors
                else "rollback_failed"
            ),
            execution_performed=bool(completed),
        )
        return count, " | ".join(errors)

    def _mark_rollback_entry(
        self,
        path: Path,
        index: int,
        state: str,
    ) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries") or []:
            if int(entry.get("index", -1)) == int(index):
                entry["state"] = state
                entry["updated_at"] = _utc_now()
                break
        data["execution_performed"] = True
        data["status"] = "running"
        self._write_json(path, data)

    def _mark_rollback_by_paths(
        self,
        path: Path,
        source: str,
        target: str,
        state: str,
    ) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries") or []:
            if (
                str(entry.get("source_path")) == source
                and str(entry.get("target_path")) == target
            ):
                entry["state"] = state
                entry["updated_at"] = _utc_now()
                break
        self._write_json(path, data)

    def _set_rollback_status(
        self,
        path: Path,
        *,
        status: str,
        execution_performed: bool,
    ) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        data["execution_performed"] = execution_performed
        data["updated_at"] = _utc_now()
        self._write_json(path, data)

    def _append_journal(
        self,
        path: Path,
        plan: RenamePlan,
        event: str,
        *,
        status: str,
        execution_performed: bool | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {
                "schema_version": 1,
                "plan_id": plan.plan_id,
                "plan_hash": plan.plan_hash,
                "events": [],
            }

        data["status"] = status
        if execution_performed is not None:
            data["execution_performed"] = execution_performed
        data.setdefault("events", []).append(
            {
                "at": _utc_now(),
                "event": event,
                "details": dict(details or {}),
            }
        )
        self._write_json(path, data)

    @staticmethod
    def _write_json(
        path: Path,
        value: dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
