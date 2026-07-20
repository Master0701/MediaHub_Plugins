from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.providers import BuiltinOnlineProvider, GenericApiProvider, GenericWebProvider


class SourceManager:
    """Lädt feste und frei definierbare Online-Quellen aus einer JSON-Datei."""

    def __init__(self, plugin_path: Path):
        self.plugin_path = Path(plugin_path)
        self.config_path = self.plugin_path / "config" / "sources.json"
        self._providers = []
        self.reload()

    def reload(self) -> None:
        data = self._read_config()
        self._providers = [self._create_provider(item) for item in (data.get("sources") or [])]

    def _read_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"schema_version": 1, "sources": []}
        with self.config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("sources.json muss ein JSON-Objekt enthalten.")
        return data

    @staticmethod
    def _create_provider(config: dict[str, Any]):
        kind = str(config.get("type") or "builtin_api").lower()
        if kind == "generic_api":
            return GenericApiProvider(config)
        if kind == "generic_web":
            return GenericWebProvider(config)
        return BuiltinOnlineProvider(config)

    def status(self) -> dict[str, Any]:
        providers = [provider.status() for provider in self._providers]
        return {
            "schema_version": 1,
            "config_path": str(self.config_path),
            "total": len(providers),
            "enabled": sum(1 for item in providers if item["enabled"]),
            "configured": sum(1 for item in providers if item["configured"]),
            "providers": providers,
        }

    def build_query(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        summary = analysis.get("summary") or {}
        return {
            "media_type": identification.get("media_type"),
            "title": identification.get("title_candidate"),
            "year": identification.get("year"),
            "season": identification.get("season"),
            "episodes": identification.get("episodes") or [],
            "duration_seconds": summary.get("duration_seconds"),
        }

    def plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
        query = self.build_query(analysis)
        candidates = []
        for provider in self._providers:
            status = provider.status()
            if status["enabled"] and status["configured"]:
                candidates.append(status["id"])
        return {
            "query": query,
            "candidate_sources": candidates,
            "executed": False,
            "reason": "Online-Abfragen sind vorbereitet, werden in dieser Version aber noch nicht automatisch ausgeführt.",
        }
