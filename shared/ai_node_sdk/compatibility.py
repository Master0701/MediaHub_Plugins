from __future__ import annotations

from dataclasses import dataclass

from .manifest import PluginManifest
from .version import SDK_VERSION, SUPPORTED_PLUGIN_API_VERSIONS


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    compatible: bool
    sdk_version: str
    plugin_api_version: str
    reason: str = ""


def check_manifest_compatibility(
    manifest: PluginManifest,
) -> CompatibilityReport:
    api_version = str(manifest.api_version).strip()

    if api_version not in SUPPORTED_PLUGIN_API_VERSIONS:
        return CompatibilityReport(
            compatible=False,
            sdk_version=SDK_VERSION,
            plugin_api_version=api_version,
            reason=(
                f"Plugin-API {api_version!r} wird von "
                f"AI-Node SDK {SDK_VERSION} nicht unterstützt."
            ),
        )

    return CompatibilityReport(
        compatible=True,
        sdk_version=SDK_VERSION,
        plugin_api_version=api_version,
    )
