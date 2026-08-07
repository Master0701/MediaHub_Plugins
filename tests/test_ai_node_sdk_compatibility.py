from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from shared.ai_node_sdk import (
    SDK_VERSION,
    audit_ai_node_plugins,
    check_manifest_compatibility,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "ai_node_plugins"
MANIFEST = (
    AI_ROOT
    / "mediahub_test_provider"
    / "plugin.json"
)


def test_sdk_final_version_is_1_0_0():
    assert SDK_VERSION == "1.0.0"


def test_reference_plugin_api_is_compatible():
    manifest = load_manifest(MANIFEST)
    report = check_manifest_compatibility(manifest)

    assert report.compatible is True
    assert report.sdk_version == "1.0.0"
    assert report.plugin_api_version == "1"


def test_unsupported_plugin_api_is_rejected():
    manifest = load_manifest(MANIFEST)
    incompatible = replace(
        manifest,
        api_version="999",
    )

    report = check_manifest_compatibility(
        incompatible
    )

    assert report.compatible is False
    assert "nicht unterstützt" in report.reason


def test_complete_ai_node_plugin_audit_is_green():
    report = audit_ai_node_plugins(AI_ROOT)

    assert report.checked_plugins >= 1
    assert report.ok is True
    assert not [
        issue
        for issue in report.issues
        if issue.level == "error"
    ]
