from __future__ import annotations

from typing import Any


class MultiQueryProviderRunner:
    """Führt alle gewichteten Suchvarianten gegen alle Provider aus."""

    def __init__(self, source_manager):
        self.source_manager = source_manager

    def run(
        self,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        providers = self.source_manager.eligible_providers(query)
        variants = self._variants(query)
        aggregated: dict[str, dict[str, Any]] = {}

        for index, variant in enumerate(variants):
            title = str(variant.get("title") or "").strip()
            if not title:
                continue

            variant_query = {
                **query,
                "title": title,
                "active_search_variant": {
                    **dict(variant),
                    "index": index,
                },
            }

            results = self._execute_provider_batch(
                providers,
                variant_query,
            )

            for provider, result in zip(
                providers,
                results,
                strict=True,
            ):
                self._merge_result(
                    aggregated,
                    provider,
                    result,
                    variant,
                    title,
                )

        return [
            self._finalize(item)
            for item in aggregated.values()
        ]

    def _execute_provider_batch(
        self,
        providers,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        executor = getattr(
            self.source_manager,
            "executor",
            None,
        )
        if executor is not None:
            return executor.execute(providers, query)

        results = []
        for provider in providers:
            try:
                results.append(provider.search(query).as_dict())
            except Exception as exc:
                results.append(
                    {
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "status": "error",
                        "matches": [],
                        "message": str(exc),
                        "cached": False,
                        "attempts": 1,
                        "error_type": type(exc).__name__,
                    }
                )
        return results

    @staticmethod
    def _variants(
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        variants = [
            dict(item)
            for item in query.get("search_variants") or []
            if isinstance(item, dict)
        ]

        if not variants:
            variants = [
                {
                    "title": query.get("title"),
                    "score": 1.0,
                    "source": "primary",
                    "reasons": [],
                }
            ]

        return variants

    @staticmethod
    def _merge_result(
        aggregated: dict[str, dict[str, Any]],
        provider,
        result: dict[str, Any],
        variant: dict[str, Any],
        title: str,
    ) -> None:
        status = provider.status()
        provider_id = str(
            result.get("provider_id")
            or provider.id
        )

        aggregate = aggregated.setdefault(
            provider_id,
            {
                "provider_id": provider_id,
                "provider_name": (
                    result.get("provider_name")
                    or provider.name
                ),
                "status": "ok",
                "matches": [],
                "message": "",
                "duration_ms": 0.0,
                "cached": True,
                "attempts": 0,
                "error_type": None,
                "priority": status["priority"],
                "trust": status["trust"],
                "provider_type": status["type"],
                "queries": [],
            },
        )

        aggregate["duration_ms"] = round(
            float(aggregate.get("duration_ms") or 0.0)
            + float(result.get("duration_ms") or 0.0),
            1,
        )
        aggregate["cached"] = bool(
            aggregate.get("cached")
            and result.get("cached")
        )
        aggregate["attempts"] = int(
            aggregate.get("attempts") or 0
        ) + int(result.get("attempts") or 1)

        aggregate["queries"].append(
            {
                "title": title,
                "score": float(
                    variant.get("score") or 0.0
                ),
                "source": variant.get("source"),
                "status": result.get("status"),
                "match_count": len(
                    result.get("matches") or []
                ),
                "cached": bool(result.get("cached")),
                "message": str(
                    result.get("message") or ""
                ),
            }
        )

        if result.get("status") in {
            "error",
            "failed",
        }:
            if not aggregate["matches"]:
                aggregate["status"] = "error"
                aggregate["message"] = str(
                    result.get("message") or ""
                )
                aggregate["error_type"] = (
                    result.get("error_type")
                )
            return

        if result.get("status") not in {
            "ok",
            "success",
            "ready",
        }:
            return

        aggregate["status"] = "ok"

        for match in result.get("matches") or []:
            aggregate["matches"].append(
                {
                    **dict(match),
                    "search_variant": title,
                    "search_variant_score": float(
                        variant.get("score") or 0.0
                    ),
                    "search_variant_source": (
                        variant.get("source")
                    ),
                    "search_variant_reasons": list(
                        variant.get("reasons") or []
                    ),
                }
            )

    @staticmethod
    def _finalize(
        aggregate: dict[str, Any],
    ) -> dict[str, Any]:
        unique: dict[
            tuple[str, str, str, str],
            dict[str, Any],
        ] = {}

        for match in aggregate.get("matches") or []:
            key = (
                str(match.get("external_id") or ""),
                str(match.get("title") or "").casefold(),
                str(match.get("year") or ""),
                str(match.get("media_type") or ""),
            )
            previous = unique.get(key)

            if (
                previous is None
                or float(
                    match.get("search_variant_score")
                    or 0.0
                )
                > float(
                    previous.get("search_variant_score")
                    or 0.0
                )
            ):
                unique[key] = match

        aggregate["matches"] = list(unique.values())
        aggregate["message"] = (
            f"{len(aggregate['matches'])} eindeutige Treffer "
            f"aus {len(aggregate['queries'])} Suchvarianten."
        )
        return aggregate
