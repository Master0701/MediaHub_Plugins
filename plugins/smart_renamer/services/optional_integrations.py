from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


METADATA_CAPABILITIES = (
    "metadata_preview",
    "metadata_read",
    "metadata_enrichment",
)


@dataclass(frozen=True, slots=True)
class IntegrationStatus:
    integration_id: str
    available: bool
    active: bool
    capability: str = ""
    provider_name: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_id": self.integration_id,
            "available": self.available,
            "active": self.active,
            "capability": self.capability,
            "provider_name": self.provider_name,
            "reason": self.reason,
        }


class OptionalIntegrationManager:
    """
    Optionale Plugin-Zusammenarbeit ohne Pflichtabhängigkeit.

    Der Smart Renamer bleibt vollständig eigenständig. Externe Provider werden
    nur genutzt, wenn sie zur Laufzeit tatsächlich vorhanden sind.

    Für Tests und zukünftige Host-Integration kann ein Provider direkt über
    ``attach_provider`` registriert werden. Zusätzlich versucht der Manager,
    einen Provider über capability-basierte Host-APIs aufzulösen, falls die
    jeweilige MediaHub-Version eine solche API bereitstellt.
    """

    def __init__(self, mediahub_api: Any = None) -> None:
        self.mediahub_api = mediahub_api
        self._providers: dict[str, Any] = {}

    def attach_provider(self, capability: str, provider: Any) -> None:
        key = str(capability).strip()
        if not key:
            raise ValueError("capability darf nicht leer sein.")
        if provider is None:
            raise ValueError("provider darf nicht None sein.")
        self._providers[key] = provider

    def detach_provider(self, capability: str) -> None:
        self._providers.pop(str(capability).strip(), None)

    def resolve(self, *capabilities: str) -> tuple[str, Any] | tuple[str, None]:
        for capability in capabilities:
            provider = self._providers.get(capability)
            if provider is not None:
                return capability, provider

        api = self.mediahub_api
        if api is None:
            return "", None

        for capability in capabilities:
            provider = self._resolve_from_host(api, capability)
            if provider is not None:
                return capability, provider

        return "", None

    def metadata_status(self) -> IntegrationStatus:
        capability, provider = self.resolve(*METADATA_CAPABILITIES)
        if provider is None:
            return IntegrationStatus(
                integration_id="metadata_editor",
                available=False,
                active=False,
                reason=(
                    "Keine passende Metadata-Editor-Capability geladen. "
                    "Smart Renamer verwendet seine interne Vorschau."
                ),
            )

        return IntegrationStatus(
            integration_id="metadata_editor",
            available=True,
            active=True,
            capability=capability,
            provider_name=self._provider_name(provider),
            reason="Optionale Metadaten-Integration aktiv.",
        )

    def enrich_items(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], IntegrationStatus]:
        status = self.metadata_status()
        if not status.active:
            return [dict(item) for item in items], status

        _, provider = self.resolve(*METADATA_CAPABILITIES)
        if provider is None:
            return [dict(item) for item in items], status

        enriched: list[dict[str, Any]] = []
        for source in items:
            item = dict(source)
            existing = dict(item.get("metadata") or {})
            external = self._metadata_for_item(provider, item)

            # Explizite Metadaten des Aufrufers haben immer Vorrang.
            combined = {**external, **existing}
            if combined:
                item["metadata"] = combined
            enriched.append(item)

        return enriched, status

    @staticmethod
    def _metadata_for_item(
        provider: Any,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        path = str(item.get("path") or "")
        if not path:
            return {}

        for name in (
            "get_metadata_for_path",
            "read_metadata",
            "metadata_for_path",
        ):
            method = getattr(provider, name, None)
            if callable(method):
                try:
                    value = method(path)
                except Exception:
                    return {}
                return dict(value or {}) if isinstance(value, dict) else {}

        return {}

    @staticmethod
    def _provider_name(provider: Any) -> str:
        for attr in ("name", "plugin_name", "id", "plugin_id"):
            value = getattr(provider, attr, None)
            if value:
                return str(value)
        return provider.__class__.__name__

    @staticmethod
    def _resolve_from_host(api: Any, capability: str) -> Any:
        """
        Defensive Capability-Auflösung.

        Es wird absichtlich keine bestimmte MediaHub-Version vorausgesetzt.
        Nicht vorhandene Host-Methoden werden ignoriert; dadurch bleibt der
        Smart Renamer auf älteren Installationen vollständig eigenständig.
        """
        for method_name in (
            "resolve_capability",
            "get_capability_provider",
            "find_capability_provider",
            "get_plugin_capability",
        ):
            method = getattr(api, method_name, None)
            if not callable(method):
                continue
            try:
                provider = method(capability)
            except Exception:
                continue
            if provider is not None:
                return provider

        manager = getattr(api, "plugin_manager", None)
        if manager is not None and manager is not api:
            return OptionalIntegrationManager._resolve_from_host(
                manager,
                capability,
            )

        return None
