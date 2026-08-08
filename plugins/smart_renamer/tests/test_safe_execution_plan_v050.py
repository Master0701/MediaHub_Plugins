from __future__ import annotations

import json
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
                        "confidence": 0.95,
                        "review_required": False,
                    }
                },
            }
        ],
        "conflicts": [],
        "skipped": [],
        "optional_integrations": {},
    }


def test_plan_is_awaiting_confirmation_and_never_auto_executes(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")

    plan = RenamePlanService().create_from_preview(
        _preview(source, "Neu.mkv")
    )

    assert plan.status == "awaiting_confirmation"
    assert plan.executable is True
    assert plan.requires_confirmation is True
    assert plan.automatic_execution is False
    assert len(plan.plan_hash) == 64


def test_same_preview_has_stable_plan_hash(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")
    service = RenamePlanService()

    first = service.create_from_preview(
        _preview(source, "Neu.mkv")
    )
    second = service.create_from_preview(
        _preview(source, "Neu.mkv")
    )

    assert first.plan_id != second.plan_id
    assert first.plan_hash == second.plan_hash


def test_blocking_preview_cannot_be_executable(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")
    preview = _preview(source, "Neu.mkv")
    preview["preview_rows"][0]["blocked"] = True
    preview["preview_rows"][0]["highest_severity"] = "blocking"
    preview["preview_rows"][0]["issues"] = [
        {
            "code": "target_exists",
            "message": "Ziel existiert",
            "severity": "blocking",
            "source": "pipeline",
        }
    ]

    plan = RenamePlanService().create_from_preview(preview)

    assert plan.status == "blocked"
    assert plan.executable is False
    assert plan.blocking_count == 1


def test_review_required_decision_blocks_execution(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")
    preview = _preview(source, "Neu.mkv")
    preview["media_items"][0]["detection_data"]["decision"][
        "review_required"
    ] = True

    plan = RenamePlanService().create_from_preview(preview)

    assert plan.status == "review_required"
    assert plan.executable is False


def test_rollback_manifest_contains_reverse_paths_without_renaming(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("daten", encoding="utf-8")
    target = tmp_path / "Neu.mkv"

    plan = RenamePlanService().create_from_preview(
        _preview(source, target.name)
    )
    service = RenameTransactionService(tmp_path)
    manifest = service.prepare_rollback_manifest(plan)

    assert source.exists()
    assert not target.exists()
    assert manifest["execution_performed"] is False
    assert manifest["entries"][0]["source_path"] == str(source)
    assert manifest["entries"][0]["target_path"] == str(target)
    assert manifest["entries"][0]["state"] == "planned"


def test_prepared_transaction_writes_only_config_files(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("daten", encoding="utf-8")
    plan = RenamePlanService().create_from_preview(
        _preview(source, "Neu.mkv")
    )

    paths = RenameTransactionService(
        tmp_path
    ).save_prepared_transaction(plan)

    assert source.exists()
    assert not (tmp_path / "Neu.mkv").exists()
    assert Path(paths["plan_path"]).is_file()
    assert Path(paths["rollback_path"]).is_file()

    rollback = json.loads(
        Path(paths["rollback_path"]).read_text(encoding="utf-8")
    )
    assert rollback["execution_performed"] is False


def test_confirmation_requires_explicit_true(tmp_path: Path):
    source = tmp_path / "Alt.mkv"
    source.write_text("x", encoding="utf-8")
    plan = RenamePlanService().create_from_preview(
        _preview(source, "Neu.mkv")
    )
    service = RenameTransactionService(tmp_path)

    with pytest.raises(ValueError):
        service.confirm(plan, user_confirmed=False)

    receipt = service.confirm(plan, user_confirmed=True)
    assert receipt.confirmed is True
    assert receipt.to_dict()["execution_unlocked"] is False
    assert len(receipt.confirmation_token) == 64


def test_transaction_execute_is_still_locked(tmp_path: Path):
    with pytest.raises(RuntimeError):
        RenameTransactionService(tmp_path).execute()


def test_plugin_execute_rename_is_still_locked():
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1],
    )

    with pytest.raises(RuntimeError):
        plugin.execute_rename()


def test_plugin_can_create_plan_without_touching_media(tmp_path: Path):
    source = tmp_path / "Film 2024.mkv"
    source.write_text("x", encoding="utf-8")
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1],
    )

    result = plugin.create_rename_plan(
        [{"path": str(source)}],
        rules=[
            {
                "type": "schema",
                "template": "[titel] ([jahr])",
            }
        ],
    )

    assert result["ok"] is True
    assert result["execution_performed"] is False
    assert source.exists()
    assert result["plan"]["requires_confirmation"] is True
