from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backends.base import RenamerBackend


class ReNamerWindowsBackend(RenamerBackend):
    backend_id = "renamer_windows"
    display_name = "ReNamer Portable"
    platform_names = ("windows",)
    priority = 10
    tool_id = "renamer"
    homepage = "https://www.den4b.com/products/renamer"
    license_name = "Lite: CC BY-NC-ND 3.0 – nur nicht-kommerziell"
    preview_bridge_ready = False
    execution_bridge_ready = False
    capabilities = (
        "rename_files",
        "rename_folders",
        "preview_changes",
        "presets",
        "regex_rules",
    )

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    @property
    def executable(self) -> Path:
        return self.base_dir / "tools" / "renamer" / "ReNamer.exe"

    def probe(self) -> dict[str, Any]:
        compatible = os.name == "nt"
        installed = compatible and self.executable.is_file()
        return {
            "backend_id": self.backend_id,
            "display_name": self.display_name,
            "installed": installed,
            "enabled": installed,
            "reachable": installed,
            "healthy": installed,
            "platform_compatible": compatible,
            "capabilities": list(self.capabilities),
            "priority": self.priority,
            "tool_id": self.tool_id,
            "homepage": self.homepage,
            "license": self.license_name,
            "preview_bridge_ready": self.preview_bridge_ready,
            "execution_bridge_ready": self.execution_bridge_ready,
            "configuration_ready": (self.executable.parent / "Settings.ini").is_file(),
            "executable": str(self.executable),
            "reason": (
                "available"
                if installed
                else (
                    "platform_not_supported"
                    if not compatible
                    else "mediahub_tool_not_installed"
                )
            ),
        }

    def preview(self, items, rules):
        raise RuntimeError(
            "Die direkte ReNamer-Preset-/Kommandozeilenübergabe ist in "
            "v0.2.0 noch nicht freigegeben. Die native Engine erstellt "
            "weiterhin die sichere Vorschau."
        )
