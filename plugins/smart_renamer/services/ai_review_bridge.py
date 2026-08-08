from __future__ import annotations

from typing import Any


class AIReviewBridge:
    CAPABILITY = "ai.rename_review"

    def __init__(self, capability_source=None):
        self.capability_source = capability_source

    def _provider(self):
        source = self.capability_source
        if source is None:
            return None

        resolve = getattr(source, "resolve", None)
        if callable(resolve):
            try:
                _, provider = resolve(self.CAPABILITY)
            except Exception:
                provider = None
            if provider is not None:
                return provider

        if isinstance(source, dict):
            provider = source.get(self.CAPABILITY)
            return provider if provider is not None else None

        if callable(source):
            try:
                provider = source(self.CAPABILITY)
            except TypeError:
                # A callable provider itself is also valid.
                return source
            return provider if provider is not None else source

        getter = getattr(source, "get_capability", None)
        if callable(getter):
            try:
                provider = getter(self.CAPABILITY)
            except Exception:
                provider = None
            if provider is not None:
                return provider

        return None

    @staticmethod
    def _provider_name(provider: Any) -> str:
        for attr in ("name", "plugin_name", "id", "plugin_id"):
            value = getattr(provider, attr, None)
            if value:
                return str(value)
        return provider.__class__.__name__

    def available(self) -> bool:
        return self._provider() is not None

    def status(self) -> dict[str, Any]:
        provider = self._provider()
        return {
            "capability": self.CAPABILITY,
            "available": provider is not None,
            "active": provider is not None,
            "optional": True,
            "provider": self._provider_name(provider) if provider is not None else "",
            "execution_allowed": False,
            "requires_human_confirmation": True,
            "human_confirmation_required": True,
        }

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = self._provider()
        if provider is None:
            return {
                **self.status(),
                "recommendation": "",
                "suggested_name": "",
                "relation_type": "",
                "confidence": 0.0,
                "rationale": "",
                "warnings": ["Kein KI-Review-Provider verfügbar."],
            }

        try:
            result = self._call_provider(provider, dict(payload or {}))
        except Exception as exc:
            return {
                **self.status(),
                "recommendation": "",
                "suggested_name": "",
                "relation_type": "",
                "confidence": 0.0,
                "rationale": "",
                "warnings": [f"KI-Review fehlgeschlagen: {exc}"],
                "provider_error": True,
            }

        result = dict(result or {})
        confidence = max(0.0, min(1.0, float(result.get("confidence") or 0.0)))
        provider_name = str(result.get("provider") or self._provider_name(provider))

        return {
            **self.status(),
            "available": True,
            "active": True,
            "provider": provider_name,
            "recommendation": str(result.get("recommendation") or ""),
            "suggested_name": str(result.get("suggested_name") or ""),
            "relation_type": str(result.get("relation_type") or ""),
            "confidence": confidence,
            "rationale": str(result.get("rationale") or ""),
            "warnings": list(result.get("warnings") or []),
            "execution_allowed": False,
            "requires_human_confirmation": True,
            "human_confirmation_required": True,
        }

    @staticmethod
    def _call_provider(provider: Any, payload: dict[str, Any]):
        if callable(provider):
            return provider(payload)

        for method_name in (
            "analyze_rename_review",
            "review_rename",
            "analyze_review",
            "analyze",
        ):
            method = getattr(provider, method_name, None)
            if callable(method):
                return method(payload)

        raise TypeError(
            "Provider besitzt keine unterstützte KI-Review-Methode."
        )
