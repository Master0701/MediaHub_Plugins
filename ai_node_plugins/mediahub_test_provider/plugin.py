from __future__ import annotations
from typing import Any

class MediaHubAITestProvider:
    plugin_id = "provider.mediahub_test"
    name = "MediaHub AI Test Provider"
    version = "1.0.0"

    def health(self) -> dict[str, Any]:
        return {
            "status": "online",
            "plugin_id": self.plugin_id,
            "plugin": self.name,
            "version": self.version,
            "message": "Das Test-Plugin wurde erfolgreich geladen.",
        }

    def test(self, value: str = "MediaHub") -> dict[str, Any]:
        return {"ok": True, "provider": self.plugin_id, "value": str(value)}
