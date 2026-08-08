from __future__ import annotations
from typing import Any

class OptionalPreviewIntegrations:
    """Optionale GUI-Brücke; ohne Capability bleibt der Renamer eigenständig."""

    def __init__(self, capability_provider=None):
        self.capability_provider = capability_provider

    def status(self) -> dict[str, Any]:
        return {
            "metadata_editor": self._handler("metadata.preview") is not None,
            "ai_assistant": self._handler("ai.rename_suggestion") is not None,
        }

    def metadata_preview(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        handler = self._handler("metadata.preview")
        return None if handler is None else handler(payload)

    def ai_suggestion(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        handler = self._handler("ai.rename_suggestion")
        return None if handler is None else handler(payload)

    def _handler(self, capability: str):
        provider = self.capability_provider
        if provider is None:
            return None
        if callable(provider):
            return provider(capability)
        getter = getattr(provider, "get_capability", None)
        if callable(getter):
            return getter(capability)
        if isinstance(provider, dict):
            value = provider.get(capability)
            return value if callable(value) else None
        return None
