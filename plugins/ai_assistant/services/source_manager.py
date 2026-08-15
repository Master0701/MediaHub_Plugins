from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.multi_query_provider_runner import MultiQueryProviderRunner
from services.query_plan import build_query_plan
from services.provider_credential_store import ProviderCredentialStore

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
    """LÃ¤dt feste und frei definierbare Online-Quellen aus einer JSON-Datei."""

    def __init__(self, plugin_path: Path, knowledge_database_path: Path | None = None):
        self.plugin_path = Path(plugin_path).resolve()
        self.default_config_path = self.plugin_path / "config" / "sources.json"

        if self.plugin_path.parent.name.casefold() == "plugins":
            base_dir = self.plugin_path.parent.parent
        else:
            plugins_parent = next(
                (
                    parent
                    for parent in self.plugin_path.parents
                    if parent.name.casefold() == "plugins"
                ),
                None,
            )
            base_dir = (
                plugins_parent.parent
                if plugins_parent is not None
                else self.plugin_path.parent
            )

        self.config_path = (
            base_dir
            / "plugin_data"
            / "ai_assistant"
            / "sources.json"
        )
        self._ensure_persistent_config()

        self.credential_store = ProviderCredentialStore(self.plugin_path)
        self.credential_store.apply_to_environment()
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
    def _load_json_file(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"schema_version": 1, "sources": []}

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise TypeError(f"{path.name} muss ein JSON-Objekt enthalten.")
        return data

    @staticmethod
    def _merge_source_configs(
        defaults: dict[str, Any],
        persistent: dict[str, Any],
    ) -> dict[str, Any]:
        """ErgÃ¤nzt neue Standardfelder, bewahrt aber Benutzereinstellungen."""
        default_sources = [
            dict(item)
            for item in (defaults.get("sources") or [])
            if isinstance(item, dict)
        ]
        persistent_sources = [
            dict(item)
            for item in (persistent.get("sources") or [])
            if isinstance(item, dict)
        ]

        persistent_by_id = {
            str(item.get("id") or ""): item
            for item in persistent_sources
            if str(item.get("id") or "")
        }

        merged_sources = []
        seen = set()

        for default in default_sources:
            provider_id = str(default.get("id") or "")
            merged = dict(default)
            if provider_id and provider_id in persistent_by_id:
                merged.update(persistent_by_id[provider_id])
            merged_sources.append(merged)
            if provider_id:
                seen.add(provider_id)

        # Benutzerdefinierte Provider, die nicht in den Standards vorkommen,
        # bleiben vollstÃ¤ndig erhalten.
        for item in persistent_sources:
            provider_id = str(item.get("id") or "")
            if provider_id and provider_id in seen:
                continue
            merged_sources.append(dict(item))

        return {
            **dict(defaults or {}),
            **{
                key: value
                for key, value in dict(persistent or {}).items()
                if key != "sources"
            },
            "schema_version": max(
                int(defaults.get("schema_version") or 1),
                int(persistent.get("schema_version") or 1),
            ),
            "sources": merged_sources,
        }

    def _ensure_persistent_config(self) -> None:
        defaults = self._load_json_file(self.default_config_path)

        if not self.config_path.exists():
            merged = defaults
        else:
            persistent = self._load_json_file(self.config_path)
            merged = self._merge_source_configs(defaults, persistent)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

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
        return self._load_json_file(self.config_path)


    def provider_config(self, provider_id: str) -> dict[str, Any] | None:
        data = self._read_config()
        for item in data.get("sources") or []:
            if str(item.get("id")) == str(provider_id):
                return dict(item)
        return None

    def update_provider_settings(
        self,
        provider_id: str,
        *,
        enabled: bool | None = None,
        language: str | None = None,
        credentials: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Persistiert GUI-Einstellungen und lÃ¤dt Provider sofort neu."""
        provider_id = str(provider_id or "").strip()
        if not provider_id:
            raise ValueError("provider_id fehlt.")

        data = self._read_config()
        sources = list(data.get("sources") or [])
        target = None

        for item in sources:
            if str(item.get("id") or "") == provider_id:
                target = item
                break

        if target is None:
            raise KeyError(f"Unbekannter Provider: {provider_id}")

        if enabled is not None:
            target["enabled"] = bool(enabled)

        if language is not None:
            value = str(language).strip()
            if value:
                target["language"] = value

        # Credentials remain outside sources.json.
        if credentials is not None:
            self.credential_store.set(provider_id, dict(credentials))

        data["sources"] = sources
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        # Important: rebuild provider instances from the just-persisted config.
        self.reload()

        provider = next(
            (item for item in self._providers if str(item.id) == provider_id),
            None,
        )
        if provider is None:
            raise RuntimeError(f"Provider nach Reload nicht gefunden: {provider_id}")

        status = dict(provider.status() or {})
        status["persisted_enabled"] = bool(target.get("enabled"))
        return status

    def provider_credentials_present(self, provider_id: str) -> dict[str, bool]:
        values = self.credential_store.get(provider_id)
        return {key: bool(str(value).strip()) for key, value in values.items()}

    def test_provider(self, provider_id: str) -> dict[str, Any]:
        self.credential_store.apply_to_environment()
        self.reload()
        provider = next((p for p in self._providers if p.id == str(provider_id)), None)
        if provider is None:
            return {"ok": False, "message": "Quelle nicht gefunden."}
        status = provider.status()
        if not status.get("enabled"):
            return {"ok": False, "message": "Quelle ist deaktiviert.", "status": status}
        if not status.get("configured"):
            return {"ok": False, "message": "Zugangsdaten fehlen.", "status": status}
        try:
            result = provider.search({"title": "12 Monkeys", "media_type": "series"}).as_dict()
            ok = result.get("status") in {"ok", "success", "ready"}
            return {"ok": ok, "message": result.get("message") or result.get("status"), "status": status}
        except Exception as exc:
            return {"ok": False, "message": str(exc), "status": status}

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

        query = {
            "schema_version": 4,
            "media_type": identification.get("media_type"),
            "title": (reasoning.get("primary_title") or identification.get("title_candidate")),
            "search_variants": reasoning.get("variants") or [],
            "query_reasoning": reasoning,
            "year": identification.get("year"),
            "season": identification.get("season"),
            "episodes": identification.get("episodes") or [],
            "duration_seconds": summary.get("duration_seconds"),
        }
        query["query_plan"] = build_query_plan(query)
        return query

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


    def resolve_episode_candidates(
        self,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Ask configured episode-capable providers for one concrete episode."""
        episode_query = {
            **dict(query or {}),
            "media_type": "series",
        }
        results = []

        for provider in self.eligible_providers(episode_query):
            resolver = getattr(provider, "resolve_episode", None)
            if not callable(resolver):
                continue
            try:
                result = dict(resolver(episode_query) or {})
            except Exception as exc:
                result = {
                    "status": "error",
                    "provider": getattr(provider, "provider_type", provider.id),
                    "provider_name": provider.name,
                    "message": str(exc),
                    "error_type": type(exc).__name__,
                }
            results.append(result)

        return results
