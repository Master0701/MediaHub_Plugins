from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CapabilityManager:
    """Verknüpft KI-Funktionen mit benötigten Werkzeugen."""

    CAPABILITY_TOOLS = {
        "media.basic_analysis": ("ffprobe", "mediainfo"),
        "media.frame_analysis": ("ffmpeg", "ffprobe"),
        "media.ocr": ("ffmpeg", "tesseract"),
        "media.mkv_analysis": ("mkvmerge",),
        "media.mkv_editing": ("mkvpropedit",),
        "knowledge.search": (),
        "quality.evaluate": ("ffprobe", "mediainfo"),
        "fingerprint.register": ("ffmpeg", "ffprobe"),
    }

    TOOL_ALIASES = {
        "mkvtoolnix": ("mkvmerge", "mkvpropedit"),
    }

    def __init__(self, plugin_path: Path, tool_resolver):
        self.plugin_path = Path(plugin_path)
        self.tool_resolver = tool_resolver

    def status(self) -> dict[str, Any]:
        manifest = self._manifest()
        declared_tools = list(manifest.get("required_tools") or [])
        tool_status = self.tool_resolver.status()

        tools = self._normalize_tools(declared_tools, tool_status)
        capabilities = {
            capability_id: self._capability_status(
                capability_id,
                required_tools,
                tools,
            )
            for capability_id, required_tools
            in self.CAPABILITY_TOOLS.items()
        }

        required_missing = [
            item["id"]
            for item in tools.values()
            if item["required"] and not item["installed"]
        ]

        optional_missing = [
            item["id"]
            for item in tools.values()
            if not item["required"] and not item["installed"]
        ]

        return {
            "ready": not required_missing,
            "required_missing": required_missing,
            "optional_missing": optional_missing,
            "tools": tools,
            "capabilities": capabilities,
            "summary": {
                "total": len(capabilities),
                "available": sum(
                    1
                    for item in capabilities.values()
                    if item["available"]
                ),
                "unavailable": sum(
                    1
                    for item in capabilities.values()
                    if not item["available"]
                ),
            },
        }

    def required_tools_for(
        self,
        capability_id: str,
    ) -> list[str]:
        return list(
            self.CAPABILITY_TOOLS.get(
                str(capability_id),
                (),
            )
        )

    def supports(self, capability_id: str) -> bool:
        item = self.status()["capabilities"].get(str(capability_id))
        return bool(item and item["available"])

    def _manifest(self) -> dict[str, Any]:
        path = self.plugin_path / "plugin.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _normalize_tools(
        self,
        declared_tools: list[dict[str, Any]],
        resolver_status: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        tools: dict[str, dict[str, Any]] = {}

        for entry in declared_tools:
            tool_id = str(entry.get("id") or "").strip().lower()
            if not tool_id:
                continue

            resolved_ids = self.TOOL_ALIASES.get(
                tool_id,
                (tool_id,),
            )

            for resolved_id in resolved_ids:
                resolved = dict(
                    resolver_status.get(resolved_id)
                    or {
                        "id": resolved_id,
                        "installed": False,
                        "path": None,
                    }
                )
                tools[resolved_id] = {
                    "id": resolved_id,
                    "declared_as": tool_id,
                    "required": bool(entry.get("required", False)),
                    "installed": bool(resolved.get("installed")),
                    "path": resolved.get("path"),
                    "provided_by": entry.get("provided_by"),
                    "feature": entry.get("feature"),
                }

        return tools

    @staticmethod
    def _capability_status(
        capability_id: str,
        required_tools: tuple[str, ...],
        tools: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        missing = [
            tool_id
            for tool_id in required_tools
            if not bool(
                (tools.get(tool_id) or {}).get("installed")
            )
        ]

        return {
            "id": capability_id,
            "available": not missing,
            "required_tools": list(required_tools),
            "missing_tools": missing,
            "reason": (
                ""
                if not missing
                else "Fehlende Werkzeuge: " + ", ".join(missing)
            ),
        }
