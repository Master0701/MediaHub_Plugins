from __future__ import annotations


class BatchAIReviewBridge:
    CAPABILITY="ai.rename_batch_review"
    FALLBACK_CAPABILITY="ai.rename_review"

    def __init__(self, capability_source=None):
        self.capability_source = capability_source

    def _resolve(self, capability):
        source = self.capability_source
        if source is None:
            return None

        # Gleiche Integrationsschicht wie beim normalen AIReviewBridge:
        # ältere/gemeinsame Registries liefern über resolve() häufig
        # (owner_id, provider) zurück.
        resolve = getattr(source, "resolve", None)
        if callable(resolve):
            try:
                resolved = resolve(capability)
            except Exception:
                resolved = None

            if isinstance(resolved, tuple):
                provider = resolved[-1] if resolved else None
            else:
                provider = resolved

            if provider is not None:
                return provider

        for name in (
            "resolve_capability",
            "get_capability_provider",
            "find_capability_provider",
            "get_plugin_capability",
            "get_capability",
        ):
            fn = getattr(source, name, None)
            if callable(fn):
                try:
                    value = fn(capability)
                except Exception:
                    value = None
                if value is not None:
                    return value

        if isinstance(source, dict):
            return source.get(capability)
        return None

    @staticmethod
    def _supports_batch(provider):
        if provider is None:
            return False
        return any(
            callable(getattr(provider, name, None))
            for name in (
                "analyze_rename_batch_review",
                "analyze_batch_review",
            )
        )

    def _provider_info(self):
        provider = self._resolve(self.CAPABILITY)
        if provider is not None:
            return provider, self.CAPABILITY, False

        # Runtime registries created before Phase 2 may still expose the same
        # KI assistant only through ai.rename_review. Reuse that provider only
        # when it really implements the Phase-2 batch contract.
        fallback = self._resolve(self.FALLBACK_CAPABILITY)
        if self._supports_batch(fallback):
            return fallback, self.FALLBACK_CAPABILITY, True

        return None, "", False

    def _provider(self):
        return self._provider_info()[0]

    @staticmethod
    def _provider_name(provider):
        for attr in ("name", "plugin_name", "id", "plugin_id"):
            value = getattr(provider, attr, None)
            if value:
                return str(value)
        return provider.__class__.__name__ if provider is not None else ""

    def status(self):
        provider, resolved_via, fallback_used = self._provider_info()
        return {
            "capability": self.CAPABILITY,
            "available": provider is not None and self._supports_batch(provider),
            "provider": self._provider_name(provider),
            "resolved_via": resolved_via,
            "fallback_used": fallback_used,
            "execution_allowed": False,
        }

    def analyze(self, payload):
        provider, _, _ = self._provider_info()
        if provider is None or not self._supports_batch(provider):
            return {
                **self.status(),
                "items": [],
                "warnings": ["Kein KI-Massenreview-Provider verfügbar."],
            }

        for name in (
            "analyze_rename_batch_review",
            "analyze_batch_review",
        ):
            fn = getattr(provider, name, None)
            if callable(fn):
                result = dict(fn(dict(payload or {})) or {})
                return {
                    **self.status(),
                    **result,
                    "available": True,
                    "execution_allowed": False,
                    "automatic_apply_allowed": False,
                    "metadata_write_allowed": False,
                    "human_confirmation_required": True,
                }

        return {
            **self.status(),
            "items": [],
            "warnings": ["Provider besitzt keine Batch-Review-Methode."],
        }
