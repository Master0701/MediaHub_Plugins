from __future__ import annotations

from pathlib import Path

from shared.ai_node_sdk import (
    load_plugin,
    read_health,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "ai_node_plugins"
    / "mediahub_test_provider"
    / "plugin.json"
)


def test_reference_plugin_loads_through_sdk():
    plugin = load_plugin(MANIFEST)

    assert plugin.manifest.plugin_id == "provider.mediahub_test"
    assert plugin.manifest.plugin_type == "provider"
    assert plugin.manifest.version == "1.0.0"

    assert plugin.capabilities == (
        "health_check",
        "test_provider",
    )

    assert plugin.has_capability("health_check") is True
    assert plugin.has_capability("test_provider") is True


def test_reference_plugin_health_is_sdk_compatible():
    plugin = load_plugin(MANIFEST)
    health = read_health(plugin)

    assert health["status"] == "online"
    assert health["plugin_id"] == "provider.mediahub_test"
    assert health["plugin"] == "MediaHub AI Test Provider"
    assert health["version"] == "1.0.0"


def test_sdk_does_not_modify_or_duplicate_capabilities():
    plugin = load_plugin(MANIFEST)

    # Die Capability-Liste kommt direkt aus plugin.json.
    assert plugin.capabilities == plugin.manifest.capability_names
    assert len(plugin.capabilities) == 2
