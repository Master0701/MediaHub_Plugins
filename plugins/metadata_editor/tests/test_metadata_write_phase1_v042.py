from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
REPO = PLUGIN_DIR.parents[1]
sys.path.insert(0, str(REPO / "shared"))

spec = importlib.util.spec_from_file_location(
    "metadata_editor_write_v042",
    PLUGIN_DIR / "plugin.py",
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
Plugin = module.MediaHubMetadataEditorPlugin


class DummyAPI:
    def __init__(self):
        self.base_dir = REPO
        self.calls = []
        self.item = {
            "id": "item-1",
            "title": "Alt",
            "series": "Serie",
            "season": 1,
            "episode": 1,
            "path": r"C:\Media\Test.mkv",
        }

    def execute_action(self, action, args):
        self.calls.append((action, args))
        if action == "metadata.update":
            self.item.update(dict(args.get("metadata") or {}))
            return {"ok": True, "message": "gespeichert"}
        return {"ok": False}

    def get_library_videos(self):
        return [dict(self.item)]


def make_plugin(tmp_path):
    plugin = Plugin.__new__(Plugin)
    plugin.plugin_path = PLUGIN_DIR
    plugin.mediahub_api = DummyAPI()
    plugin.base_dir = tmp_path
    plugin.data_dir = tmp_path / "plugin_data" / "metadata_editor"
    plugin.backup_dir = plugin.data_dir / "backups"
    plugin.recovery_dir = plugin.data_dir / "recovery"
    return plugin


def payload(**extra):
    data = {
        "id": "item-1",
        "original": {
            "id": "item-1",
            "title": "Alt",
            "series": "Serie",
            "season": 1,
            "episode": 1,
            "path": r"C:\Media\Test.mkv",
        },
        "edited": {
            "id": "item-1",
            "title": "Neu",
            "series": "Serie",
            "season": 1,
            "episode": 1,
            "path": r"C:\Media\Test.mkv",
        },
    }
    data.update(extra)
    return data


def test_write_capability_only_available_with_execute_action(tmp_path):
    plugin = make_plugin(tmp_path)
    caps = plugin.get_runtime_capabilities()
    assert caps["metadata.write"] is plugin
    contract = plugin.get_capability_contracts()["metadata.write"]
    assert contract["mode"] == "confirmed_write"
    assert contract["available"] is True
    assert contract["execution_allowed"] is True
    assert contract["automatic_apply_allowed"] is False
    assert contract["human_confirmation_required"] is True


def test_metadata_write_rejects_missing_human_confirmation(tmp_path):
    plugin = make_plugin(tmp_path)
    result = plugin.write_metadata(payload())
    assert result["ok"] is False
    assert result["confirmation_required"] is True
    assert plugin.mediahub_api.calls == []


def test_confirmed_metadata_write_uses_mediahub_action_and_verifies(tmp_path):
    plugin = make_plugin(tmp_path)
    result = plugin.write_metadata(
        payload(confirmed=True, confirmation_source="human_gui")
    )
    assert result["ok"] is True
    assert result["verification"]["verified"] is True
    assert plugin.mediahub_api.item["title"] == "Neu"
    assert plugin.mediahub_api.calls[0][0] == "metadata.update"
    confirmation = plugin.mediahub_api.calls[0][1]["confirmation"]
    assert confirmation["confirmed"] is True
    assert confirmation["source"] == "human_gui"
    recovery_files = list(plugin.recovery_dir.glob("*.json"))
    assert len(recovery_files) >= 2


def test_commit_route_delegates_to_confirmed_write(tmp_path):
    plugin = make_plugin(tmp_path)
    status, content_type, body = plugin._commit(payload())
    assert status == 409
    assert content_type == "application/json; charset=utf-8"
    assert b"confirmation_required" in body


def test_gui_contains_explicit_metadata_apply_button():
    text = (PLUGIN_DIR / "plugin.py").read_text(encoding="utf-8")
    assert 'QPushButton("Metadaten übernehmen…")' in text
    assert "self.btn_commit.clicked.connect(self._commit_metadata)" in text
    assert '"confirmation_source": "human_gui"' in text
