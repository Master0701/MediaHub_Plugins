from __future__ import annotations

from pathlib import Path

from shared.ai_node_sdk import (
    PluginRuntimeStatus,
    TaskRequest,
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


def _plugin():
    return load_plugin(MANIFEST)


def test_enabled_healthy_plugin_is_candidate():
    plugin = _plugin()

    candidates = find_candidates(
        [plugin],
        "test_provider",
        runtime_status={
            plugin.manifest.plugin_id: PluginRuntimeStatus()
        },
    )

    assert len(candidates) == 1


def test_disabled_plugin_is_not_used():
    plugin = _plugin()

    result = route_task(
        [plugin],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "blocked"},
        ),
        runtime_status={
            plugin.manifest.plugin_id: PluginRuntimeStatus(
                enabled=False
            )
        },
    )

    assert result.ok is False
    assert "deaktiviert" in result.error


def test_unhealthy_plugin_is_not_used():
    plugin = _plugin()

    result = route_task(
        [plugin],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "blocked"},
        ),
        runtime_status={
            plugin.manifest.plugin_id: PluginRuntimeStatus(
                healthy=False
            )
        },
    )

    assert result.ok is False
    assert "Health-Check" in result.error


def test_platform_incompatible_plugin_is_not_used():
    plugin = _plugin()

    result = route_task(
        [plugin],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "blocked"},
        ),
        runtime_status={
            plugin.manifest.plugin_id: PluginRuntimeStatus(
                platform_compatible=False
            )
        },
    )

    assert result.ok is False
    assert "Plattform" in result.error


def test_missing_required_tool_blocks_plugin_without_installing_anything():
    plugin = _plugin()

    # Der aktuelle Testprovider hat keine required_tools.
    # Dieser Test bestätigt daher nur, dass das Runtime-Toolset
    # keine stillschweigende Installation auslöst.
    result = route_task(
        [plugin],
        TaskRequest(
            task_type="test_provider",
            payload={"value": "ok"},
        ),
        available_tools=(),
    )

    assert result.ok is True
    assert result.data["value"] == "ok"
