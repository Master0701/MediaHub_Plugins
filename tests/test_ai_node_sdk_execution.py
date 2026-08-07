from __future__ import annotations

from pathlib import Path

from shared.ai_node_sdk import (
    TaskRequest,
    execute_task,
    find_candidates,
    load_plugin,
    route_task,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "ai_node_plugins"
    / "mediahub_test_provider"
    / "plugin.json"
)


def test_declared_test_provider_capability_maps_to_existing_test_method():
    plugin = load_plugin(MANIFEST)

    task = TaskRequest(
        task_type="test_provider",
        payload={"value": "MediaHub"},
    )

    result = execute_task(plugin, task)

    assert result.ok is True
    assert result.backend == "provider.mediahub_test"
    assert result.data["provider"] == "provider.mediahub_test"
    assert result.data["value"] == "MediaHub"


def test_undeclared_capability_is_blocked_before_execution():
    plugin = load_plugin(MANIFEST)

    result = execute_task(
        plugin,
        TaskRequest(
            task_type="rename_files",
            payload={},
        ),
    )

    assert result.ok is False
    assert "rename_files" in result.error


def test_router_uses_only_manifest_capabilities():
    plugin = load_plugin(MANIFEST)

    candidates = find_candidates(
        [plugin],
        "test_provider",
    )

    assert len(candidates) == 1
    assert candidates[0].plugin_id == "provider.mediahub_test"

    result = route_task(
        [plugin],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "Router"},
        ),
    )

    assert result.ok is True
    assert result.data["value"] == "Router"


def test_router_reports_unavailable_capability():
    plugin = load_plugin(MANIFEST)

    result = route_task(
        [plugin],
        TaskRequest(
            task_type="ocr",
            payload={},
        ),
    )

    assert result.ok is False
    assert "Keine installierte AI-Node-Erweiterung" in result.error
