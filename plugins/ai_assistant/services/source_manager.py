from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.multi_query_provider_runner import MultiQueryProviderRunner

from services.search_variant_reasoner import SearchVariantReasoner
from services.source_selection_policy import SourceSelectionPolicy

from services.providers import (
    ProviderExecutor,
    ProviderRegistry,
    ProviderResultCache,
    BuiltinOnlineProvider,
    GenericApiProvider,
    GenericWebProvider,
    TmdbProvider,
    TvdbProvider,
    WikipediaProvider,
)


class SourceManager:
    """Lädt feste und frei definierbare Online-Quellen aus einer JSON-Datei."""

    def __init__(self, plugin_path: Path, knowledge_database_path: Path | None = None):
        self.plugin_path = Path(plugin_path)
        self.config_path = self.plugin_path / "config" / "sources.json"
        self.registry = self._build_registry()
        self.query_reasoner = SearchVariantReasoner(knowledge_database_path)
        self.multi_query_runner = MultiQueryProviderRunner(self)
        self.cache = ProviderResultCache(
            self.plugin_path / "cache" / "providers"
        )
        self.executor = ProviderExecutor(self.cache, max_workers=4)
        self._providers = []
        self._last_execution = None
        self.reload()

    @staticmethod
    def _build_registry() -> ProviderRegistry:
        registry = ProviderRegistry()
        registry.register("tmdb", TmdbProvider)
        registry.register("tvdb", TvdbProvider, aliases=("thetvdb",))
        registry.register("wikipedia", WikipediaProvider)
        registry.register("generic_api", GenericApiProvider)
        registry.register("generic_web", GenericWebProvider)
        registry.register("builtin_api", BuiltinOnlineProvider)
        return registry

    def reload(self) -> None:
        data = self._read_config()
        self._providers = [
            self.registry.create(item)
            for item in (data.get("sources") or [])
        ]

    def _read_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"schema_version": 1, "sources": []}
        with self.config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise TypeError("sources.json muss ein JSON-Objekt enthalten.")
        return data

    def status(self) -> dict[str, Any]:
        providers = [provider.status() for provider in self._providers]
        return {
            "schema_version": 3,
            "framework_version": 1,
            "config_path": str(self.config_path),
            "total": len(providers),
            "enabled": sum(1 for item in providers if item["enabled"]),
            "configured": sum(1 for item in providers if item["configured"]),
            "supported_types": self.registry.supported_types(),
            "parallel_execution": True,
            "max_workers": self.executor.max_workers,
            "cache": self.cache.stats(),
            "last_execution": self._last_execution,
            "providers": providers,
        }

    def build_query(
        self,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        summary = analysis.get("summary") or {}
        reasoning = self.query_reasoner.build(analysis)

        return {
            "media_type": identification.get("media_type"),
            "title": (
                reasoning.get("primary_title")
                or identification.get("title_candidate")
            ),
            "search_variants": reasoning.get("variants") or [],
            "query_reasoning": reasoning,
            "year": identification.get("year"),
            "season": identification.get("season"),
            "episodes": identification.get("episodes") or [],
            "duration_seconds": summary.get("duration_seconds"),
        }

    def _supports_query(
        self,
        provider,
        query: dict[str, Any],
    ) -> bool:
        return SourceSelectionPolicy.provider_supports(
            list(provider.config.get("media_types") or []),
            query,
        )

    def eligible_providers(self, query: dict[str, Any]):
        providers = []
        for provider in self._providers:
            status = provider.status()
            if status["enabled"] and status["configured"] and self._supports_query(provider, query):
                providers.append(provider)
        return sorted(
            providers,
            key=lambda item: int(item.config.get("priority", 50)),
            reverse=True,
        )

    def plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
        query = self.build_query(analysis)
        candidates = [provider.status() for provider in self.eligible_providers(query)]
        return {
            "query": query,
            "candidate_sources": [item["id"] for item in candidates],
            "candidate_details": candidates,
            "executed": False,
            "selection_mode": SourceSelectionPolicy.selection_mode(
                query,
            ),
            "reason": SourceSelectionPolicy.selection_reason(
                query,
                len(candidates),
            ),
        }

    def execute(
        self,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        results = self.multi_query_runner.run(query)

        self._last_execution = {
            "query": dict(query),
            "providers": len(results),
            "search_variants": len(
                query.get("search_variants") or []
            ),
            "successful": sum(
                1
                for item in results
                if item.get("status")
                in {"ok", "success"}
            ),
            "failed": sum(
                1
                for item in results
                if item.get("status")
                in {"error", "failed"}
            ),
            "queries": sum(
                len(item.get("queries") or [])
                for item in results
            ),
            "matches": sum(
                len(item.get("matches") or [])
                for item in results
            ),
        }
        return results
