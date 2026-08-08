from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from plugin import MediaHubSmartRenamerPlugin
from services.rename_plan import RenamePlanService
from services.transaction_service import RenameTransactionService


def _preview(source: Path, target_name: str) -> dict:
    return {
        "status": "preview_ready",
        "selected_backend": "mediahub_native",
        "preview_rows": [
            {
                "index": 0,
                "source_path": str(source),
                "original_name": source.name,
                "proposed_name": target_name,
                "target_path": str(source.with_name(target_name)),
                "changed": target_name != source.name,
                "item_type": "file",
                "backend_id": "mediahub_native",
                "rule_sources": ["schema"],
                "issues": [],
                "blocked": False,
                "highest_severity": "info",
                "metadata": {},
            }
        ],
        "media_items": [
            {
                "path": str(source),
                "detection_data": {
                    "decision": {
                        "selected_candidate_id": "local-primary",
                        "state": "preview_selected",
                        "confidence": 0.96,
                        "review_required": False,
                    }
                },
            }
        ],
        "conflicts": [],
        "skipped": [],
        "optional_integrations": {},
    }


def _plan(source: Path, target_name: str):
    return RenamePlanService().create_from_preview(
        _preview(source, target_name)
    )


def test_real_rename_requires_confirmation_token(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = _plan(source, "Neu.mkv")
    service = RenameTransactionService(tmp_path)

    with pytest.raises(PermissionError):
        service.execute(plan, confirmation_token="")

    assert source.exists()
    assert not (tmp_path / "Neu.mkv").exists()


def test_confirmed_transaction_renames_file(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    target = tmp_path / "Neu.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = _plan(source, target.name)

    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)
    result = service.execute(
        plan,
        confirmation_token=receipt.confirmation_token,
    )

    assert result.ok is True
    assert result.status == "completed"
    assert result.renamed_count == 1
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "daten"


def test_confirmation_token_is_single_use(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = _plan(source, "Neu.mkv")
    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)

    first = service.execute(
        plan,
        confirmation_token=receipt.confirmation_token,
    )
    assert first.ok is True

    with pytest.raises(PermissionError):
        service.execute(
            plan,
            confirmation_token=receipt.confirmation_token,
        )


def test_changed_plan_hash_is_rejected(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = _plan(source, "Neu.mkv")
    tampered = replace(plan, plan_hash="0" * 64)

    service = RenameTransactionService(tmp_path)
    with pytest.raises(RuntimeError):
        service.confirm(tampered, user_confirmed=True)

    assert source.exists()


def test_existing_target_is_rechecked_before_commit(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    target = tmp_path / "Neu.mkv"
    source.write_text("quelle", encoding="utf-8")
    plan = _plan(source, target.name)

    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)

    # Ziel entsteht erst NACH Vorschau/Bestätigung.
    target.write_text("fremd", encoding="utf-8")

    with pytest.raises(RuntimeError):
        service.execute(
            plan,
            confirmation_token=receipt.confirmation_token,
        )

    assert source.exists()
    assert target.read_text(encoding="utf-8") == "fremd"


def test_cross_directory_move_is_blocked_in_v052(tmp_path: Path):
    source_dir = tmp_path / "a"
    target_dir = tmp_path / "b"
    source_dir.mkdir()
    target_dir.mkdir()
    source = source_dir / "Alt.mkv"
    source.write_text("x", encoding="utf-8")

    preview = _preview(source, "Neu.mkv")
    preview["preview_rows"][0]["target_path"] = str(
        target_dir / "Neu.mkv"
    )
    plan = RenamePlanService().create_from_preview(preview)

    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)

    with pytest.raises(RuntimeError):
        service.execute(
            plan,
            confirmation_token=receipt.confirmation_token,
        )

    assert source.exists()


def test_manual_rollback_restores_completed_transaction(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    target = tmp_path / "Neu.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = _plan(source, target.name)
    service = RenameTransactionService(tmp_path)
    service.save_prepared_transaction(plan)
    receipt = service.confirm(plan, user_confirmed=True)

    result = service.execute(
        plan,
        confirmation_token=receipt.confirmation_token,
    )
    assert result.ok is True
    assert target.exists()

    rollback = service.rollback_transaction(plan)
    assert rollback.ok is True
    assert rollback.status == "rolled_back"
    assert source.exists()
    assert not target.exists()


def test_journal_and_rollback_are_persisted(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")
    plan = _plan(source, "Neu.mkv")
    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)

    result = service.execute(
        plan,
        confirmation_token=receipt.confirmation_token,
    )
    folder = Path(result.transaction_dir)

    journal = json.loads(
        (folder / "journal.json").read_text(encoding="utf-8")
    )
    rollback = json.loads(
        (folder / "rollback.json").read_text(encoding="utf-8")
    )

    assert journal["status"] == "completed"
    assert any(
        event["event"] == "item_renamed"
        for event in journal["events"]
    )
    assert rollback["status"] == "completed"
    assert rollback["entries"][0]["state"] == "renamed"


def test_automatic_rollback_after_partial_failure(tmp_path: Path, monkeypatch):
    first = tmp_path / "A.mkv"
    second = tmp_path / "B.mkv"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")

    preview = {
        "status": "preview_ready",
        "selected_backend": "mediahub_native",
        "preview_rows": [],
        "media_items": [],
        "conflicts": [],
        "skipped": [],
        "optional_integrations": {},
    }
    for index, (source, target_name) in enumerate(
        ((first, "A-neu.mkv"), (second, "B-neu.mkv"))
    ):
        preview["preview_rows"].append(
            {
                "index": index,
                "source_path": str(source),
                "original_name": source.name,
                "proposed_name": target_name,
                "target_path": str(source.with_name(target_name)),
                "changed": True,
                "backend_id": "mediahub_native",
                "rule_sources": ["test"],
                "issues": [],
                "blocked": False,
                "highest_severity": "info",
                "metadata": {},
            }
        )
        preview["media_items"].append(
            {
                "path": str(source),
                "detection_data": {
                    "decision": {
                        "review_required": False,
                    }
                },
            }
        )

    plan = RenamePlanService().create_from_preview(preview)
    service = RenameTransactionService(tmp_path)
    receipt = service.confirm(plan, user_confirmed=True)

    original_rename = Path.rename
    calls = {"count": 0}

    def failing_rename(self, target):
        calls["count"] += 1
        # first forward rename succeeds; second forward rename fails;
        # rollback rename must then be allowed to run.
        if calls["count"] == 2:
            raise OSError("simulierter Fehler")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", failing_rename)

    result = service.execute(
        plan,
        confirmation_token=receipt.confirmation_token,
    )

    assert result.ok is False
    assert result.status == "rolled_back"
    assert result.renamed_count == 1
    assert result.rolled_back_count == 1
    assert first.exists()
    assert second.exists()
    assert not (tmp_path / "A-neu.mkv").exists()
    assert not (tmp_path / "B-neu.mkv").exists()


def test_plugin_execute_facade_requires_plan_and_token():
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1],
    )

    with pytest.raises(PermissionError):
        plugin.execute_rename()


def test_web_ui_still_has_no_execute_endpoint():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")

    assert "/smart-renamer/api/execute" not in html
    assert "Direkte Web-Ausführung gesperrt" in html
