from __future__ import annotations

from collections.abc import Callable
from typing import Any

from services.providers.base_provider import BaseProvider


ProviderFactory = Callable[[dict[str, Any]], BaseProvider]


class ProviderRegistry:
    def __init__(self):
        self._factories: dict[str, ProviderFactory] = {}

    def register(
        self,
        provider_type: str,
        factory: ProviderFactory,
        *,
        aliases: tuple[str, ...] = (),
    ) -> None:
        for key in (provider_type, *aliases):
            normalized = str(key).strip().casefold()
            if normalized:
                self._factories[normalized] = factory

    def create(self, config: dict[str, Any]) -> BaseProvider:
        provider_type = str(
            config.get("type") or config.get("id") or "builtin_api"
        ).casefold()
        provider_id = str(config.get("id") or "").casefold()
        factory = (
            self._factories.get(provider_type)
            or self._factories.get(provider_id)
            or self._factories.get("builtin_api")
        )
        if factory is None:
            raise KeyError(
                f"Kein Provider für Typ '{provider_type}' registriert."
            )
        return factory(config)

    def supported_types(self) -> list[str]:
        return sorted(self._factories)
