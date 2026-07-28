from __future__ import annotations

from typing import Any

from services.online_result_ranker import OnlineResultRanker


class OnlineAgent:
    """Führt geeignete Quellen aus und vereinheitlicht deren Ergebnisse."""

    def __init__(self, source_manager):
        self.source_manager = source_manager
        self.ranker = OnlineResultRanker()

    def run(
        self,
        analysis: dict,
    ) -> dict:
        source_plan = analysis.get("source_plan") or {}
        planned_query = source_plan.get("query")

        query = (
            dict(planned_query)
            if isinstance(planned_query, dict)
            else self.source_manager.build_query(analysis)
        )

        provider_results = self.source_manager.execute(
            query
        )
        ranking = self.ranker.rank(
            query,
            provider_results,
        )

        return {
            "schema_version": 3,
            "executed": True,
            "query": query,
            "provider_results": provider_results,
            "ranking": ranking,
            "successful_sources": sum(
                1
                for item in provider_results
                if item.get("status")
                in {"ok", "success", "ready"}
            ),
            "failed_sources": sum(
                1
                for item in provider_results
                if item.get("status")
                in {"error", "failed"}
            ),
            "search_variant_count": len(
                query.get("search_variants") or []
            ),
            "executed_queries": sum(
                len(item.get("queries") or [])
                for item in provider_results
            ),
        }
