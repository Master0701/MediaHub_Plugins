from pathlib import Path
from types import SimpleNamespace

import pytest

from plugin import MediaHubSmartRenamerPlugin


class DummyTransactionService:
    def __init__(self):
        self.confirm_called = False
        self.execute_called = False

    def confirm(self, plan, user_confirmed):
        assert user_confirmed is True
        self.confirm_called = True
        return SimpleNamespace(
            confirmation_token="token-123",
            to_dict=lambda: {"confirmation_token": "token-123"},
        )

    def execute(self, plan, confirmation_token):
        assert confirmation_token == "token-123"
        self.execute_called = True
        return SimpleNamespace(
            ok=True,
            status="completed",
            to_dict=lambda: {"ok": True, "status": "completed"},
        )


class DummyPlan:
    def __init__(self, executable=True, status="awaiting_confirmation"):
        self.executable = executable
        self.status = status

    def to_dict(self):
        return {
            "executable": self.executable,
            "status": self.status,
        }


def build_plugin(tmp_path):
    plugin = MediaHubSmartRenamerPlugin.__new__(MediaHubSmartRenamerPlugin)
    plugin.transaction_service = DummyTransactionService()
    plugin.rename_plan_service = SimpleNamespace(
        create_from_preview=lambda preview: DummyPlan(executable=True)
    )
    plugin.preview_rename = lambda items, rules=None, preferred_backend=None: {
        "status": "ok",
        "items": items,
    }
    return plugin


def test_handoff_requires_metadata_editor_confirmation(tmp_path):
    plugin = build_plugin(tmp_path)

    with pytest.raises(PermissionError):
        plugin.execute_metadata_editor_handoff(
            [
                {
                    "path": str(tmp_path / "movie.mkv"),
                    "metadata": {"title": "Movie"},
                }
            ],
            metadata_editor_confirmed=False,
        )

    assert plugin.transaction_service.confirm_called is False
    assert plugin.transaction_service.execute_called is False


def test_confirmed_handoff_executes_via_transaction_service(tmp_path):
    plugin = build_plugin(tmp_path)

    result = plugin.execute_metadata_editor_handoff(
        [
            {
                "path": str(tmp_path / "movie.mkv"),
                "metadata": {"title": "Movie"},
            }
        ],
        metadata_editor_confirmed=True,
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["confirmation_source"] == "metadata_editor"
    assert result["automatic_execution"] is True
    assert result["execution_performed"] is True
    assert plugin.transaction_service.confirm_called is True
    assert plugin.transaction_service.execute_called is True


def test_blocked_plan_never_executes(tmp_path):
    plugin = build_plugin(tmp_path)
    plugin.rename_plan_service = SimpleNamespace(
        create_from_preview=lambda preview: DummyPlan(
            executable=False,
            status="review_required",
        )
    )

    result = plugin.execute_metadata_editor_handoff(
        [
            {
                "path": str(tmp_path / "movie.mkv"),
                "metadata": {"title": "Movie"},
            }
        ],
        metadata_editor_confirmed=True,
    )

    assert result["ok"] is False
    assert result["automatic_execution"] is False
    assert result["execution_performed"] is False
    assert result["requires_manual_review"] is True
    assert plugin.transaction_service.confirm_called is False
    assert plugin.transaction_service.execute_called is False


def test_handoff_rejects_missing_metadata(tmp_path):
    plugin = build_plugin(tmp_path)

    with pytest.raises(ValueError):
        plugin.execute_metadata_editor_handoff(
            [{"path": str(tmp_path / "movie.mkv")}],
            metadata_editor_confirmed=True,
        )

    assert plugin.transaction_service.confirm_called is False
    assert plugin.transaction_service.execute_called is False


def test_runtime_capability_is_exposed():
    plugin = MediaHubSmartRenamerPlugin.__new__(MediaHubSmartRenamerPlugin)

    caps = plugin.get_runtime_capabilities()
    contracts = plugin.get_capability_contracts()

    assert caps["rename.metadata_handoff"] is plugin

    contract = contracts["rename.metadata_handoff"]
    assert contract["mode"] == "confirmed_handoff"
    assert contract["execution_allowed"] is True
    assert contract["automatic_apply_allowed"] is True
    assert contract["human_confirmation_required"] is False
    assert contract["confirmation_source_required"] == "metadata_editor"
