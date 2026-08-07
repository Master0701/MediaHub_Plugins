from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capability import Capability
from .version import SUPPORTED_PLUGIN_API_VERSIONS


@dataclass(frozen=True, slots=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    plugin_type: str
    entrypoint: str
    api_version: str
    description: str
    author: str
    license_name: str
    enabled_by_default: bool
    capabilities: tuple[Capability, ...]
    permissions: tuple[str, ...]
    dependencies: tuple[str, ...]
    required_tools: tuple[str, ...]

    @property
    def capability_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.capabilities)

    @property
    def api_supported(self) -> bool:
        return self.api_version in SUPPORTED_PLUGIN_API_VERSIONS


def _strings(data: Any, field: str) -> tuple[str, ...]:
    value = data.get(field, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} muss eine Liste sein.")

    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise ValueError(f"{field} enthält einen leeren Eintrag.")
        if text not in result:
            result.append(text)
    return tuple(result)


def load_manifest(path: str | Path) -> PluginManifest:
    manifest_path = Path(path)
    raw = manifest_path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(
            f"UTF-8-BOM ist im Plugin-Manifest nicht erlaubt: {manifest_path}"
        )

    data = json.loads(raw.decode("utf-8"))

    required = (
        "id",
        "name",
        "version",
        "type",
        "entrypoint",
        "api_version",
    )
    missing = [
        field
        for field in required
        if not str(data.get(field, "")).strip()
    ]
    if missing:
        raise ValueError(
            "Pflichtfelder fehlen: " + ", ".join(missing)
        )

    capability_names = _strings(data, "capabilities")

    return PluginManifest(
        plugin_id=str(data["id"]).strip(),
        name=str(data["name"]).strip(),
        version=str(data["version"]).strip(),
        plugin_type=str(data["type"]).strip(),
        entrypoint=str(data["entrypoint"]).strip(),
        api_version=str(data["api_version"]).strip(),
        description=str(data.get("description") or "").strip(),
        author=str(data.get("author") or "").strip(),
        license_name=str(data.get("license") or "").strip(),
        enabled_by_default=bool(
            data.get("enabled_by_default", False)
        ),
        capabilities=tuple(
            Capability(name)
            for name in capability_names
        ),
        permissions=_strings(data, "permissions"),
        dependencies=_strings(data, "dependencies"),
        required_tools=_strings(data, "required_tools"),
    )
