from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass(slots=True)
class ProviderResult:
    provider_id: str
    provider_name: str
    status: str
    matches: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""
    duration_ms: float | None = None
    cached: bool = False
    attempts: int = 1
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "status": self.status,
            "matches": list(self.matches),
            "message": self.message,
            "duration_ms": self.duration_ms,
            "cached": self.cached,
            "attempts": self.attempts,
            "error_type": self.error_type,
        }


class BaseProvider:
    provider_type = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = dict(config)
        self.id = str(config.get("id") or "unknown")
        self.name = str(config.get("name") or self.id)
        self.enabled = bool(config.get("enabled", False))

    @property
    def timeout(self) -> float:
        return max(1.0, float(self.config.get("timeout", 20)))

    @property
    def retries(self) -> int:
        return max(0, min(5, int(self.config.get("retries", 1))))

    @property
    def cache_ttl_seconds(self) -> int:
        return max(0, int(self.config.get("cache_ttl_seconds", 21600)))

    def status(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.provider_type,
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "media_types": list(self.config.get("media_types") or []),
            "priority": int(self.config.get("priority", 50)),
            "trust": float(self.config.get("trust", 0.5)),
            "timeout": self.timeout,
            "retries": self.retries,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    def is_configured(self) -> bool:
        return self.enabled

    def search(self, query: dict[str, Any]) -> ProviderResult:
        return ProviderResult(
            self.id,
            self.name,
            "not_implemented",
            message="Provider-Grundklasse",
        )

    def timed_search(self, query: dict[str, Any]) -> ProviderResult:
        started = perf_counter()
        result = self.search(query)
        result.duration_ms = round((perf_counter() - started) * 1000, 1)
        return result
