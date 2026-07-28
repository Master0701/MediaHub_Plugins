from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Any

from services.providers.base_provider import BaseProvider
from services.providers.cache import ProviderResultCache


class ProviderExecutor:
    def __init__(
        self,
        cache: ProviderResultCache,
        *,
        max_workers: int = 4,
    ):
        self.cache = cache
        self.max_workers = max(1, min(8, int(max_workers)))

    def _execute_one(
        self,
        provider: BaseProvider,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        cached = self.cache.get(
            provider.id,
            query,
            provider.cache_ttl_seconds,
        )
        if cached is not None:
            cached["cached"] = True
            cached["duration_ms"] = 0.0
            return cached

        started = perf_counter()
        try:
            result = provider.timed_search(query).as_dict()
        except Exception as exc:
            result = {
                "provider_id": provider.id,
                "provider_name": provider.name,
                "status": "error",
                "matches": [],
                "message": str(exc),
                "duration_ms": round(
                    (perf_counter() - started) * 1000,
                    1,
                ),
                "cached": False,
                "attempts": provider.retries + 1,
                "error_type": type(exc).__name__,
            }

        if result.get("status") in {"ok", "success"}:
            self.cache.put(provider.id, query, result)
        return result

    def execute(
        self,
        providers: list[BaseProvider],
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not providers:
            return []
        indexed = {}
        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(providers)),
            thread_name_prefix="mediahub-provider",
        ) as pool:
            futures = {
                pool.submit(self._execute_one, provider, query): index
                for index, provider in enumerate(providers)
            }
            for future in as_completed(futures):
                indexed[futures[future]] = future.result()
        return [indexed[index] for index in sorted(indexed)]
