from __future__ import annotations

from pathlib import Path

from shared.ai_node_sdk import (
    HealthStatus,
    SDK_VERSION,
    TaskRequest,
    TaskResult,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
TEST_PLUGIN_MANIFEST = (
    ROOT
    / "ai_node_plugins"
    / "mediahub_test_provider"
    / "plugin.json"
)


def test_sdk_version():
    assert SDK_VERSION == "1.0.0"


def test_existing_ai_plugin_manifest_is_source_of_truth():
    manifest = load_manifest(TEST_PLUGIN_MANIFEST)

    assert manifest.plugin_id == "provider.mediahub_test"
    assert manifest.version == "1.0.0"
    assert manifest.plugin_type == "provider"
    assert manifest.api_version == "1"
    assert manifest.api_supported is True
    assert manifest.capability_names == (
        "health_check",
        "test_provider",
    )
    assert manifest.required_tools == ()
    assert manifest.permissions == ()


def test_health_status_matches_existing_health_shape():
    status = HealthStatus(
        status="online",
        plugin_id="provider.mediahub_test",
        plugin="MediaHub AI Test Provider",
        version="1.0.0",
        message="OK",
    )

    assert status.to_dict()["status"] == "online"
    assert status.to_dict()["plugin_id"] == (
        "provider.mediahub_test"
    )


def test_task_models_are_generic_and_do_not_duplicate_capabilities():
    request = TaskRequest(
        task_type="test_provider",
        payload={"value": "MediaHub"},
    )
    result = TaskResult.success(
        {"value": "MediaHub"},
        backend="provider.mediahub_test",
    )

    assert request.task_type == "test_provider"
    assert result.ok is True
    assert result.backend == "provider.mediahub_test"
